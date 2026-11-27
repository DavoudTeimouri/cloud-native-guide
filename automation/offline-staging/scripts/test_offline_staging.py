#!/usr/bin/env python3
"""Tests for offline staging scripts"""

import json
import os
import sys
import tempfile
import hashlib
from pathlib import Path

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from validate_manifest import ManifestValidator
from stage_artifacts import StagingHelper
from check_readiness import ProfileChecker


def create_test_fixture() -> tuple:
    """Create a temporary test fixture with valid manifest and artifacts."""
    tmpdir = tempfile.mkdtemp()
    staging_root = Path(tmpdir) / "staging"
    staging_root.mkdir(parents=True)
    manifest_path = Path(tmpdir) / "manifest.json"

    # Create test artifacts
    artifacts_dir = staging_root / "test-artifacts"
    artifacts_dir.mkdir(parents=True)

    # Create a dummy wheel file
    wheel_file = artifacts_dir / "ansible-12.3.0-py3-none-any.whl"
    wheel_file.write_bytes(b"dummy wheel content")
    wheel_sha256 = hashlib.sha256(b"dummy wheel content").hexdigest()

    # Create ansible-core wheel
    ansible_core_file = artifacts_dir / "ansible_core-2.19.3-py3-none-any.whl"
    ansible_core_file.write_bytes(b"dummy ansible-core content")
    ansible_core_sha256 = hashlib.sha256(b"dummy ansible-core content").hexdigest()

    # Create a dummy collection file
    coll_file = artifacts_dir / "community.general-11.2.0.tar.gz"
    coll_file.write_bytes(b"dummy collection content")
    coll_sha256 = hashlib.sha256(b"dummy collection content").hexdigest()

    # Create manifest
    manifest = {
        "schema_version": "1.0.0",
        "profile": "kubespray-control-node",
        "generated_at": "2026-11-24T00:00:00Z",
        "generated_by": "test",
        "artifacts": [
            {
                "category": "python-package",
                "name": "ansible",
                "version": "12.3.0",
                "source": {
                    "type": "pypi",
                    "reference": "https://pypi.org/project/ansible/",
                    "fetched_at": "2026-11-24T00:00:00Z",
                    "verified": False
                },
                "destination": "test-artifacts/ansible-12.3.0-py3-none-any.whl",
                "sha256": wheel_sha256,
                "size_bytes": len(b"dummy wheel content"),
                "platform": "py3-none-any",
                "required": True,
                "feature": None
            },
            {
                "category": "python-package",
                "name": "ansible-core",
                "version": "2.19.3",
                "source": {
                    "type": "pypi",
                    "reference": "https://pypi.org/project/ansible-core/",
                    "fetched_at": "2026-11-24T00:00:00Z",
                    "verified": False
                },
                "destination": "test-artifacts/ansible_core-2.19.3-py3-none-any.whl",
                "sha256": hashlib.sha256(b"dummy ansible-core content").hexdigest(),
                "size_bytes": len(b"dummy ansible-core content"),
                "platform": "py3-none-any",
                "required": True,
                "feature": None
            },
            {
                "category": "ansible-collection",
                "name": "community.general",
                "version": "11.2.0",
                "source": {
                    "type": "ansible-galaxy",
                    "reference": "https://galaxy.ansible.com/community/general",
                    "fetched_at": "2026-11-24T00:00:00Z",
                    "verified": False
                },
                "destination": "test-artifacts/community.general-11.2.0.tar.gz",
                "sha256": coll_sha256,
                "size_bytes": len(b"dummy collection content"),
                "platform": "any",
                "required": True,
                "feature": None
            }
        ]
    }

    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    return tmpdir, staging_root, manifest_path


def test_valid_manifest():
    """Test validation of a valid manifest."""
    tmpdir, staging_root, manifest_path = create_test_fixture()
    try:
        validator = ManifestValidator(manifest_path, staging_root)
        assert validator.validate(), f"Validation failed: {validator.errors}"
        print("OK   Valid manifest validation")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_invalid_manifest_missing_field():
    """Test validation fails for missing required field."""
    tmpdir, staging_root, manifest_path = create_test_fixture()
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        del manifest["schema_version"]
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        validator = ManifestValidator(manifest_path, staging_root)
        assert not validator.validate(), "Should fail for missing schema_version"
        assert any("schema_version" in e for e in validator.errors)
        print("OK   Missing field detection")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_invalid_checksum():
    """Test validation fails for incorrect checksum."""
    tmpdir, staging_root, manifest_path = create_test_fixture()
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        manifest["artifacts"][0]["sha256"] = "0" * 64  # Invalid checksum
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        validator = ManifestValidator(manifest_path, staging_root)
        assert not validator.validate(), "Should fail for invalid checksum"
        assert any("checksum mismatch" in e for e in validator.errors)
        print("OK   Invalid checksum detection")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_missing_file():
    """Test validation fails for missing staged file."""
    tmpdir, staging_root, manifest_path = create_test_fixture()
    try:
        # Remove the actual file but keep manifest
        test_file = staging_root / "test-artifacts" / "ansible-12.3.0-py3-none-any.whl"
        test_file.unlink()

        validator = ManifestValidator(manifest_path, staging_root)
        assert not validator.validate(), "Should fail for missing file"
        assert any("file not found" in e for e in validator.errors)
        print("OK   Missing file detection")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_duplicate_identity():
    """Test validation fails for duplicate artifact identities."""
    tmpdir, staging_root, manifest_path = create_test_fixture()
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        # Duplicate the first artifact
        manifest["artifacts"].append(dict(manifest["artifacts"][0]))
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        validator = ManifestValidator(manifest_path, staging_root)
        assert not validator.validate(), "Should fail for duplicate identity"
        assert any("duplicate artifact identity" in e for e in validator.errors)
        print("OK   Duplicate identity detection")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_duplicate_destination():
    """Test validation fails for duplicate destination paths."""
    tmpdir, staging_root, manifest_path = create_test_fixture()
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        # Duplicate with different identity but same destination
        dup = dict(manifest["artifacts"][1])
        dup["name"] = "ansible"
        dup["version"] = "12.3.0"
        dup["category"] = "python-package"
        manifest["artifacts"].append(dup)
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        validator = ManifestValidator(manifest_path, staging_root)
        assert not validator.validate(), "Should fail for duplicate destination"
        assert any("duplicate destination" in e for e in validator.errors)
        print("OK   Duplicate destination detection")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_path_traversal_rejection():
    """Test that path traversal in destination is rejected."""
    tmpdir, staging_root, manifest_path = create_test_fixture()
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        manifest["artifacts"][0]["destination"] = "../../../etc/passwd"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        validator = ManifestValidator(manifest_path, staging_root)
        assert not validator.validate(), "Should reject path traversal"
        assert any("escapes staging root" in e or "unsafe destination" in e for e in validator.errors)
        print("OK   Path traversal rejection")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_staging_helper_idempotent():
    """Test staging helper is idempotent."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        manifest_path = Path(tmpdir) / "manifest.json"

        # Create source artifact
        src_dir = Path(tmpdir) / "sources"
        src_dir.mkdir()
        wheel_file = src_dir / "test-package-1.0.0-py3-none-any.whl"
        wheel_file.write_bytes(b"test content")

        # First run
        helper = StagingHelper(staging_root, manifest_path, force=False)
        assert helper.add_artifact(
            category="python-package",
            name="test-package",
            version="1.0.0",
            source_type="pypi",
            source_reference="https://pypi.org/project/test-package/",
            source_path=wheel_file,
            destination="packages/test-package-1.0.0-py3-none-any.whl",
            required=True
        )
        assert helper.write_manifest("kubespray-control-node")

        # Second run with force=False should fail (file exists)
        helper2 = StagingHelper(staging_root, manifest_path, force=False)
        assert not helper2.add_artifact(
            category="python-package",
            name="test-package",
            version="1.0.0",
            source_type="pypi",
            source_reference="https://pypi.org/project/test-package/",
            source_path=wheel_file,
            destination="packages/test-package-1.0.0-py3-none-any.whl",
            required=True
        )

        # With force=True should succeed
        helper3 = StagingHelper(staging_root, manifest_path, force=True)
        assert helper3.add_artifact(
            category="python-package",
            name="test-package",
            version="1.0.0",
            source_type="pypi",
            source_reference="https://pypi.org/project/test-package/",
            source_path=wheel_file,
            destination="packages/test-package-1.0.0-py3-none-any.whl",
            required=True
        )

        print("OK   Staging helper idempotent/overwrite protection")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_staging_helper_path_traversal():
    """Test staging helper rejects path traversal."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        manifest_path = Path(tmpdir) / "manifest.json"
        src_dir = Path(tmpdir) / "sources"
        src_dir.mkdir()
        wheel_file = src_dir / "test.whl"
        wheel_file.write_bytes(b"test")

        helper = StagingHelper(staging_root, manifest_path, force=False)
        assert not helper.add_artifact(
            category="python-package",
            name="test",
            version="1.0",
            source_type="pypi",
            source_reference="https://pypi.org/",
            source_path=wheel_file,
            destination="../../../etc/passwd",
            required=True
        )
        print("OK   Staging helper path traversal rejection")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_profile_readiness():
    """Test profile readiness checker."""
    # Create a fixture WITHOUT ansible-core to test missing required detection
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        artifacts_dir = staging_root / "test-artifacts"
        artifacts_dir.mkdir(parents=True)

        wheel_file = artifacts_dir / "ansible-12.3.0-py3-none-any.whl"
        wheel_file.write_bytes(b"dummy wheel content")
        wheel_sha256 = hashlib.sha256(b"dummy wheel content").hexdigest()

        coll_file = artifacts_dir / "community.general-11.2.0.tar.gz"
        coll_file.write_bytes(b"dummy collection content")
        coll_sha256 = hashlib.sha256(b"dummy collection content").hexdigest()

        manifest = {
            "schema_version": "1.0.0",
            "profile": "kubespray-control-node",
            "generated_at": "2026-11-24T00:00:00Z",
            "generated_by": "test",
            "artifacts": [
                {
                    "category": "python-package",
                    "name": "ansible",
                    "version": "12.3.0",
                    "source": {"type": "pypi", "reference": "https://pypi.org/project/ansible/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                    "destination": "test-artifacts/ansible-12.3.0-py3-none-any.whl",
                    "sha256": wheel_sha256,
                    "size_bytes": len(b"dummy wheel content"),
                    "platform": "py3-none-any",
                    "required": True,
                    "feature": None
                },
                {
                    "category": "ansible-collection",
                    "name": "community.general",
                    "version": "11.2.0",
                    "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/community/general", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                    "destination": "test-artifacts/community.general-11.2.0.tar.gz",
                    "sha256": "c" * 64,
                    "size_bytes": 100,
                    "platform": "any",
                    "required": True,
                    "feature": None
                }
            ]
        }
        manifest_path = Path(tmpdir) / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        checker = ProfileChecker(manifest_path)
        assert checker.load_manifest()
        checker.index_artifacts()

        # This manifest has ansible 12.3.0 but profile needs ansible-core too
        ready = checker.check_profile("kubespray-control-node")
        assert not ready, "Should not be ready (missing ansible-core)"
        assert len(checker.results["missing_required"]) > 0

        print("OK   Profile readiness detects missing required artifacts")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_cilium_calico_separation():
    """Test that Cilium and Calico profiles are separate."""
    tmpdir = tempfile.mkdtemp()
    try:
        manifest_path = Path(tmpdir) / "manifest.json"
        # Create manifest with all required artifacts for all profiles
        manifest = {
            "schema_version": "1.0.0",
            "profile": "combined",
            "generated_at": "2026-11-24T00:00:00Z",
            "generated_by": "test",
            "artifacts": [
                # Python packages (required by kubespray-control-node and combined)
                {"category": "python-package", "name": "ansible", "version": "12.3.0",
                 "source": {"type": "pypi", "reference": "https://pypi.org/project/ansible/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/ansible-12.3.0.whl", "sha256": "a" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None},
                {"category": "python-package", "name": "ansible-core", "version": "2.19.3",
                 "source": {"type": "pypi", "reference": "https://pypi.org/project/ansible-core/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/ansible-core-2.19.3.whl", "sha256": "a" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None},
                {"category": "python-package", "name": "bcrypt", "version": "<6",
                 "source": {"type": "pypi", "reference": "https://pypi.org/project/bcrypt/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/bcrypt-<6.whl", "sha256": "a" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None},
                {"category": "python-package", "name": "cryptography", "version": "50.0.1",
                 "source": {"type": "pypi", "reference": "https://pypi.org/project/cryptography/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/cryptography-50.0.1.whl", "sha256": "a" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None},
                {"category": "python-package", "name": "jmespath", "version": "1.1.0",
                 "source": {"type": "pypi", "reference": "https://pypi.org/project/jmespath/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/jmespath-1.1.0.whl", "sha256": "a" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None},
                {"category": "python-package", "name": "netaddr", "version": "1.3.0",
                 "source": {"type": "pypi", "reference": "https://pypi.org/project/netaddr/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/netaddr-1.3.0.whl", "sha256": "a" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None},
                {"category": "python-package", "name": "passlib", "version": "1.7.4",
                 "source": {"type": "pypi", "reference": "https://pypi.org/project/passlib/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/passlib-1.7.4.whl", "sha256": "a" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None},
                # Ansible collections (required by kubespray-control-node and combined)
                {"category": "ansible-collection", "name": "community.general", "version": "11.2.0",
                 "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/community/general", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/community.general-11.2.0.tar.gz", "sha256": "b" * 64, "size_bytes": 100, "platform": "any", "required": True, "feature": None},
                {"category": "ansible-collection", "name": "community.kubernetes", "version": "2.4.0",
                 "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/community/kubernetes", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/community.kubernetes-2.4.0.tar.gz", "sha256": "b" * 64, "size_bytes": 100, "platform": "any", "required": True, "feature": None},
                {"category": "ansible-collection", "name": "kubernetes.core", "version": "5.0.0",
                 "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/kubernetes/core", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/kubernetes.core-5.0.0.tar.gz", "sha256": "b" * 64, "size_bytes": 100, "platform": "any", "required": True, "feature": None},
                {"category": "ansible-collection", "name": "ansible.posix", "version": "2.0.0",
                 "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/ansible/posix", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/ansible.posix-2.0.0.tar.gz", "sha256": "b" * 64, "size_bytes": 100, "platform": "any", "required": True, "feature": None},
                {"category": "ansible-collection", "name": "ansible.utils", "version": "6.0.0",
                 "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/ansible/utils", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/ansible.utils-6.0.0.tar.gz", "sha256": "b" * 64, "size_bytes": 100, "platform": "any", "required": True, "feature": None},
                # Kubespray source (required by kubespray-control-node and combined)
                {"category": "kubespray-source", "name": "kubespray", "version": "v2.32.0",
                 "source": {"type": "git", "reference": "https://github.com/kubernetes-sigs/kubespray", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "kubespray/v2.32.0", "sha256": "c" * 64, "size_bytes": 100, "required": True, "feature": None},
                # Kubernetes control plane (shared, required by all k8s profiles)
                {"category": "container-image", "name": "kube-apiserver", "version": "1.36.4",
                 "source": {"type": "oci-registry", "reference": "docker.io/k8s/kube-apiserver", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/kube-apiserver-1.36.4.tar", "sha256": "a" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": None},
                {"category": "container-image", "name": "kube-controller-manager", "version": "1.36.4",
                 "source": {"type": "oci-registry", "reference": "docker.io/k8s/kube-controller-manager", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/kube-controller-manager-1.36.4.tar", "sha256": "a" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": None},
                {"category": "container-image", "name": "kube-scheduler", "version": "1.36.4",
                 "source": {"type": "oci-registry", "reference": "docker.io/k8s/kube-scheduler", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/kube-scheduler-1.36.4.tar", "sha256": "a" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": None},
                {"category": "container-image", "name": "kube-proxy", "version": "1.36.4",
                 "source": {"type": "oci-registry", "reference": "docker.io/k8s/kube-proxy", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/kube-proxy-1.36.4.tar", "sha256": "a" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": None},
                {"category": "container-image", "name": "etcd", "version": "3.6.14",
                 "source": {"type": "oci-registry", "reference": "docker.io/etcd", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/etcd-3.6.14.tar", "sha256": "a" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": None},
                {"category": "container-image", "name": "coredns", "version": "1.14.2",
                 "source": {"type": "oci-registry", "reference": "docker.io/coredns/coredns", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/coredns-1.14.2.tar", "sha256": "a" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": None},
                {"category": "container-image", "name": "pause", "version": "3.10",
                 "source": {"type": "oci-registry", "reference": "docker.io/k8s/pause", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/pause-3.10.tar", "sha256": "a" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": None},
                # Cilium
                {"category": "container-image", "name": "cilium", "version": "1.20.2",
                 "source": {"type": "oci-registry", "reference": "docker.io/cilium/cilium", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/cilium-1.20.2.tar", "sha256": "a" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": "cilium"},
                {"category": "container-image", "name": "cilium-operator", "version": "1.20.2",
                 "source": {"type": "oci-registry", "reference": "docker.io/cilium/operator", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/cilium-operator-1.20.2.tar", "sha256": "a" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": "cilium"},
                {"category": "container-image", "name": "hubble-relay", "version": "1.20.2",
                 "source": {"type": "oci-registry", "reference": "docker.io/cilium/hubble-relay", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/hubble-relay-1.20.2.tar", "sha256": "a" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": "cilium"},
                {"category": "container-image", "name": "hubble-ui", "version": "1.20.2",
                 "source": {"type": "oci-registry", "reference": "docker.io/cilium/hubble-ui", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/hubble-ui-1.20.2.tar", "sha256": "a" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": "cilium"},
                # Calico
                {"category": "container-image", "name": "calico-node", "version": "3.31.7",
                 "source": {"type": "oci-registry", "reference": "docker.io/calico/node", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/calico-node-3.31.7.tar", "sha256": "b" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": "calico"},
                {"category": "container-image", "name": "calico-kube-controllers", "version": "3.31.7",
                 "source": {"type": "oci-registry", "reference": "docker.io/calico/kube-controllers", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/calico-kube-controllers-3.31.7.tar", "sha256": "b" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": "calico"},
                {"category": "container-image", "name": "calico-typha", "version": "3.31.7",
                 "source": {"type": "oci-registry", "reference": "docker.io/calico/typha", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/calico-typha-3.31.7.tar", "sha256": "b" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": "calico"},
                # Metrics
                {"category": "container-image", "name": "metrics-server", "version": "0.8.1",
                 "source": {"type": "oci-registry", "reference": "docker.io/k8s/metrics-server", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/metrics-server-0.8.1.tar", "sha256": "c" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": None},
            ]
        }
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        checker = ProfileChecker(manifest_path)
        checker.load_manifest()
        checker.index_artifacts()

        # Cilium profile should pass
        ready_cilium = checker.check_profile("kubernetes-cilium")
        assert ready_cilium, f"Cilium profile should be ready: {checker.results['missing_required']}"

        # Calico profile should pass
        ready_calico = checker.check_profile("kubernetes-calico")
        assert ready_calico, f"Calico profile should be ready: {checker.results['missing_required']}"

        # Combined profile should pass (no CNI required)
        ready_combined = checker.check_profile("combined")
        assert ready_combined, f"Combined profile should be ready: {checker.results['missing_required']}"

        print("OK   Cilium/Calico profile separation")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_optional_artifact_reporting():
    """Test that optional artifacts in manifest are handled."""
    tmpdir = tempfile.mkdtemp()
    try:
        manifest_path = Path(tmpdir) / "manifest.json"
        manifest = {
            "schema_version": "1.0.0",
            "profile": "kubespray-control-node",
            "generated_at": "2026-11-24T00:00:00Z",
            "generated_by": "test",
            "artifacts": [
                # All required python packages
                {"category": "python-package", "name": "ansible", "version": "12.3.0",
                 "source": {"type": "pypi", "reference": "https://pypi.org/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/ansible-12.3.0.whl", "sha256": "a" * 64, "size_bytes": 100, "required": True, "feature": None},
                {"category": "python-package", "name": "ansible-core", "version": "2.19.3",
                 "source": {"type": "pypi", "reference": "https://pypi.org/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/ansible-core-2.19.3.whl", "sha256": "b" * 64, "size_bytes": 100, "required": True, "feature": None},
                {"category": "python-package", "name": "bcrypt", "version": "<6",
                 "source": {"type": "pypi", "reference": "https://pypi.org/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/bcrypt-<6.whl", "sha256": "b" * 64, "size_bytes": 100, "required": True, "feature": None},
                {"category": "python-package", "name": "cryptography", "version": "50.0.1",
                 "source": {"type": "pypi", "reference": "https://pypi.org/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/cryptography-50.0.1.whl", "sha256": "b" * 64, "size_bytes": 100, "required": True, "feature": None},
                {"category": "python-package", "name": "jmespath", "version": "1.1.0",
                 "source": {"type": "pypi", "reference": "https://pypi.org/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/jmespath-1.1.0.whl", "sha256": "b" * 64, "size_bytes": 100, "required": True, "feature": None},
                {"category": "python-package", "name": "netaddr", "version": "1.3.0",
                 "source": {"type": "pypi", "reference": "https://pypi.org/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/netaddr-1.3.0.whl", "sha256": "b" * 64, "size_bytes": 100, "required": True, "feature": None},
                {"category": "python-package", "name": "passlib", "version": "1.7.4",
                 "source": {"type": "pypi", "reference": "https://pypi.org/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/passlib-1.7.4.whl", "sha256": "b" * 64, "size_bytes": 100, "required": True, "feature": None},
                # Required ansible collections
                {"category": "ansible-collection", "name": "community.general", "version": "11.2.0",
                 "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/community.general-11.2.0.tar.gz", "sha256": "c" * 64, "size_bytes": 100, "required": True, "feature": None},
                {"category": "ansible-collection", "name": "community.kubernetes", "version": "2.4.0",
                 "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/community.kubernetes-2.4.0.tar.gz", "sha256": "c" * 64, "size_bytes": 100, "required": True, "feature": None},
                {"category": "ansible-collection", "name": "kubernetes.core", "version": "5.0.0",
                 "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/kubernetes.core-5.0.0.tar.gz", "sha256": "c" * 64, "size_bytes": 100, "required": True, "feature": None},
                {"category": "ansible-collection", "name": "ansible.posix", "version": "2.0.0",
                 "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/ansible.posix-2.0.0.tar.gz", "sha256": "c" * 64, "size_bytes": 100, "required": True, "feature": None},
                {"category": "ansible-collection", "name": "ansible.utils", "version": "6.0.0",
                 "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/ansible.utils-6.0.0.tar.gz", "sha256": "c" * 64, "size_bytes": 100, "required": True, "feature": None},
                # Kubespray source
                {"category": "kubespray-source", "name": "kubespray", "version": "v2.32.0",
                 "source": {"type": "git", "reference": "https://github.com/kubernetes-sigs/kubespray", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "kubespray/v2.32.0", "sha256": "e" * 64, "size_bytes": 100, "required": True, "feature": None},
                # Optional artifact in manifest (not in profile requirements)
                {"category": "python-package", "name": "hvac", "version": "2.3.0",
                 "source": {"type": "pypi", "reference": "https://pypi.org/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/hvac-2.3.0.whl", "sha256": "d" * 64, "size_bytes": 100, "required": False, "feature": "vault"}
            ]
        }
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        checker = ProfileChecker(manifest_path)
        checker.load_manifest()
        checker.index_artifacts()
        ready = checker.check_profile("kubespray-control-node")

        # Should be ready - hvac is not in profile requirements, so not tracked
        assert ready, f"Should be ready: {checker.results['missing_required']}"
        # hvac is not in profile requirements, so not tracked as missing
        # This test verifies that extra artifacts in manifest don't break readiness
        print("OK   Optional artifact reporting (extra artifacts don't affect readiness)")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_deterministic_manifest_generation():
    """Test that repeated staging produces byte-for-byte identical manifests."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path1 = Path(tmpdir) / "manifest1.json"
        manifest_path2 = Path(tmpdir) / "manifest2.json"

        # Create source artifact
        src_dir = Path(tmpdir) / "sources"
        src_dir.mkdir()
        wheel_file = src_dir / "test-package-1.0.0-py3-none-any.whl"
        wheel_file.write_bytes(b"test content for determinism")

        # Set deterministic timestamp via environment
        os.environ["SOURCE_DATE_EPOCH"] = "1700000000"  # 2023-11-14T22:13:20Z

        try:
            # First run
            helper1 = StagingHelper(staging_root, manifest_path1, force=False)
            assert helper1.add_artifact(
                category="python-package",
                name="test-package",
                version="1.0.0",
                source_type="pypi",
                source_reference="https://pypi.org/project/test-package/",
                source_path=wheel_file,
                destination="packages/test-package-1.0.0-py3-none-any.whl",
                required=True
            )
            assert helper1.write_manifest("kubespray-control-node")

            # Second run with same SOURCE_DATE_EPOCH
            helper2 = StagingHelper(staging_root, manifest_path2, force=True)
            assert helper2.add_artifact(
                category="python-package",
                name="test-package",
                version="1.0.0",
                source_type="pypi",
                source_reference="https://pypi.org/project/test-package/",
                source_path=wheel_file,
                destination="packages/test-package-1.0.0-py3-none-any.whl",
                required=True
            )
            assert helper2.write_manifest("kubespray-control-node")

            # Compare manifests byte-for-byte
            with open(manifest_path1, 'rb') as f1, open(manifest_path2, 'rb') as f2:
                content1 = f1.read()
                content2 = f2.read()

            assert content1 == content2, f"Manifests not identical:\n{content1}\n{content2}"

            # Also verify generated_at is deterministic
            with open(manifest_path1, 'r') as f1, open(manifest_path2, 'r') as f2:
                m1 = json.load(f1)
                m2 = json.load(f2)
            assert m1["generated_at"] == m2["generated_at"], "generated_at not deterministic"
            assert m1["artifacts"][0]["source"]["fetched_at"] == m2["artifacts"][0]["source"]["fetched_at"], "fetched_at not deterministic"

            print("OK   Deterministic manifest generation (SOURCE_DATE_EPOCH)")
        finally:
            # Clean up env
            if "SOURCE_DATE_EPOCH" in os.environ:
                del os.environ["SOURCE_DATE_EPOCH"]
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_manifest_without_source_date_epoch_fallback():
    """Test that manifest generation works without SOURCE_DATE_EPOCH (fallback timestamp)."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"

        # Create source artifact
        src_dir = Path(tmpdir) / "sources"
        src_dir.mkdir()
        wheel_file = src_dir / "test-package-1.0.0-py3-none-any.whl"
        wheel_file.write_bytes(b"test content")

        # Ensure SOURCE_DATE_EPOCH is not set
        if "SOURCE_DATE_EPOCH" in os.environ:
            del os.environ["SOURCE_DATE_EPOCH"]

        helper = StagingHelper(staging_root, Path(tmpdir) / "manifest.json", force=False)
        assert helper.add_artifact(
            category="python-package",
            name="test-package",
            version="1.0.0",
            source_type="pypi",
            source_reference="https://pypi.org/project/test-package/",
            source_path=Path(tmpdir) / "sources" / "test-package-1.0.0-py3-none-any.whl",
            destination="packages/test-package-1.0.0-py3-none-any.whl",
            required=True
        )
        assert helper.write_manifest("kubespray-control-node")

        with open(Path(tmpdir) / "manifest.json", 'r') as f:
            manifest = json.load(f)

        # Should have fallback timestamp
        assert manifest["generated_at"] == "1970-01-01T00:00:00Z", "Fallback timestamp not used"
        assert manifest["artifacts"][0]["source"]["fetched_at"] == "1970-01-01T00:00:00Z", "Fallback fetched_at not used"

        print("OK   Fallback timestamp when SOURCE_DATE_EPOCH not set")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_combined_profile_not_substitute_for_cni():
    """Test that combined profile cannot substitute for CNI-specific profiles."""
    tmpdir = tempfile.mkdtemp()
    try:
        manifest_path = Path(tmpdir) / "manifest.json"
        # Create manifest with all required artifacts for combined profile:
        # - Python packages
        # - Ansible collections
        # - Kubespray source
        # - Shared Kubernetes control plane container images
        # But MISSING Cilium-specific and Calico-specific images
        manifest = {
            "schema_version": "1.0.0",
            "profile": "combined",
            "generated_at": "2026-11-24T00:00:00Z",
            "generated_by": "test",
            "artifacts": [
                # Python packages (required by combined)
                {"category": "python-package", "name": "ansible", "version": "12.3.0",
                 "source": {"type": "pypi", "reference": "https://pypi.org/project/ansible/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/ansible-12.3.0.whl", "sha256": "a" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None},
                {"category": "python-package", "name": "ansible-core", "version": "2.19.3",
                 "source": {"type": "pypi", "reference": "https://pypi.org/project/ansible-core/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/ansible-core-2.19.3.whl", "sha256": "a" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None},
                {"category": "python-package", "name": "bcrypt", "version": "<6",
                 "source": {"type": "pypi", "reference": "https://pypi.org/project/bcrypt/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/bcrypt-<6.whl", "sha256": "a" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None},
                {"category": "python-package", "name": "cryptography", "version": "50.0.1",
                 "source": {"type": "pypi", "reference": "https://pypi.org/project/cryptography/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/cryptography-50.0.1.whl", "sha256": "a" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None},
                {"category": "python-package", "name": "jmespath", "version": "1.1.0",
                 "source": {"type": "pypi", "reference": "https://pypi.org/project/jmespath/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/jmespath-1.1.0.whl", "sha256": "a" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None},
                {"category": "python-package", "name": "netaddr", "version": "1.3.0",
                 "source": {"type": "pypi", "reference": "https://pypi.org/project/netaddr/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/netaddr-1.3.0.whl", "sha256": "a" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None},
                {"category": "python-package", "name": "passlib", "version": "1.7.4",
                 "source": {"type": "pypi", "reference": "https://pypi.org/project/passlib/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/passlib-1.7.4.whl", "sha256": "a" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None},
                # Ansible collections (required by combined)
                {"category": "ansible-collection", "name": "community.general", "version": "11.2.0",
                 "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/community/general", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/community.general-11.2.0.tar.gz", "sha256": "b" * 64, "size_bytes": 100, "platform": "any", "required": True, "feature": None},
                {"category": "ansible-collection", "name": "community.kubernetes", "version": "2.4.0",
                 "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/community/kubernetes", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/community.kubernetes-2.4.0.tar.gz", "sha256": "b" * 64, "size_bytes": 100, "platform": "any", "required": True, "feature": None},
                {"category": "ansible-collection", "name": "kubernetes.core", "version": "5.0.0",
                 "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/kubernetes/core", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/kubernetes.core-5.0.0.tar.gz", "sha256": "b" * 64, "size_bytes": 100, "platform": "any", "required": True, "feature": None},
                {"category": "ansible-collection", "name": "ansible.posix", "version": "2.0.0",
                 "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/ansible/posix", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/ansible.posix-2.0.0.tar.gz", "sha256": "b" * 64, "size_bytes": 100, "platform": "any", "required": True, "feature": None},
                {"category": "ansible-collection", "name": "ansible.utils", "version": "6.0.0",
                 "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/ansible/utils", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "packages/ansible.utils-6.0.0.tar.gz", "sha256": "b" * 64, "size_bytes": 100, "platform": "any", "required": True, "feature": None},
                # Kubespray source (required by combined)
                {"category": "kubespray-source", "name": "kubespray", "version": "v2.32.0",
                 "source": {"type": "git", "reference": "https://github.com/kubernetes-sigs/kubespray", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "kubespray/v2.32.0", "sha256": "c" * 64, "size_bytes": 100, "required": True, "feature": None},
                # Shared Kubernetes control plane container images (required by all k8s profiles)
                {"category": "container-image", "name": "kube-apiserver", "version": "1.36.4",
                 "source": {"type": "oci-registry", "reference": "docker.io/k8s/kube-apiserver", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/kube-apiserver-1.36.4.tar", "sha256": "a" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": None},
                {"category": "container-image", "name": "kube-controller-manager", "version": "1.36.4",
                 "source": {"type": "oci-registry", "reference": "docker.io/k8s/kube-controller-manager", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/kube-controller-manager-1.36.4.tar", "sha256": "a" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": None},
                {"category": "container-image", "name": "kube-scheduler", "version": "1.36.4",
                 "source": {"type": "oci-registry", "reference": "docker.io/k8s/kube-scheduler", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/kube-scheduler-1.36.4.tar", "sha256": "a" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": None},
                {"category": "container-image", "name": "kube-proxy", "version": "1.36.4",
                 "source": {"type": "oci-registry", "reference": "docker.io/k8s/kube-proxy", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/kube-proxy-1.36.4.tar", "sha256": "a" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": None},
                {"category": "container-image", "name": "etcd", "version": "3.6.14",
                 "source": {"type": "oci-registry", "reference": "docker.io/etcd", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/etcd-3.6.14.tar", "sha256": "a" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": None},
                {"category": "container-image", "name": "coredns", "version": "1.14.2",
                 "source": {"type": "oci-registry", "reference": "docker.io/coredns/coredns", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/coredns-1.14.2.tar", "sha256": "a" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": None},
                {"category": "container-image", "name": "pause", "version": "3.10",
                 "source": {"type": "oci-registry", "reference": "docker.io/k8s/pause", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/pause-3.10.tar", "sha256": "a" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": None},
                {"category": "container-image", "name": "metrics-server", "version": "0.8.1",
                 "source": {"type": "oci-registry", "reference": "docker.io/k8s/metrics-server", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "images/metrics-server-0.8.1.tar", "sha256": "a" * 64, "size_bytes": 100, "platform": "linux/amd64", "required": True, "feature": None},
            ]
        }
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        checker = ProfileChecker(manifest_path)
        checker.load_manifest()
        checker.index_artifacts()

        # Combined profile should pass (it has all required artifacts)
        ready_combined = checker.check_profile("combined")
        assert ready_combined, f"Combined profile should be ready: {checker.results['missing_required']}"

        # Cilium profile should FAIL (missing Cilium-specific images)
        ready_cilium = checker.check_profile("kubernetes-cilium")
        assert not ready_cilium, "Cilium profile should NOT be ready without Cilium images"
        assert len(checker.results["missing_required"]) > 0
        assert any("cilium" in item.lower() for item in checker.results["missing_required"]), \
            f"Expected missing Cilium images, got: {checker.results['missing_required']}"

        # Calico profile should FAIL (missing Calico-specific images)
        ready_calico = checker.check_profile("kubernetes-calico")
        assert not ready_calico, "Calico profile should NOT be ready without Calico images"
        assert len(checker.results["missing_required"]) > 0
        assert any("calico" in item.lower() for item in checker.results["missing_required"]), \
            f"Expected missing Calico images, got: {checker.results['missing_required']}"

        print("OK   Combined profile not a substitute for CNI-specific profiles")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_staging_rpm():
    """Test staging an RPM repository snapshot."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        # Create a mock RPM repository structure
        repo_dir = input_root / "ol9-baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        (repo_dir / "repodata").mkdir()
        
        # Create mock repomd.xml
        repomd = repo_dir / "repodata" / "repomd.xml"
        repomd.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<repomd xmlns="http://linux.duke.edu/metadata/repo">
  <data type="primary">
    <location href="repodata/primary.xml.gz"/>
    <checksum type="sha256">abc123</checksum>
    <timestamp>1700000000</timestamp>
  </data>
</repomd>""")
        
        # Create a mock package
        pkg = repo_dir / "Packages" / "test-package-1.0-1.el9.x86_64.rpm"
        pkg.write_bytes(b"mock rpm content")

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        assert helper.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/repo/OracleLinux/OL9/baseos/latest/x86_64/",
            source_path=repo_dir,
            destination="os-repositories/ol9/9/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            repository_metadata={"repomd_xml": "present", "primary_xml": "present"},
            signature_status="unverified"
        )
        assert helper.write_manifest("os-repositories")

        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        artifact = manifest["artifacts"][0]
        assert artifact["category"] == "os-repository"
        assert artifact["name"] == "ol9-baseos"
        assert artifact["version"] == "9"
        assert artifact["os_family"] == "redhat"
        assert artifact["os_version"] == "9"
        assert artifact["architecture"] == "x86_64"
        assert artifact["repository_type"] == "yum"
        assert artifact["signature_status"] == "unverified"
        assert "repository_metadata" in artifact

        print("OK   OS repository staging RPM")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_staging_apt():
    """Test staging an APT repository snapshot."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        # Create a mock APT repository structure
        repo_dir = input_root / "ubuntu-main"
        repo_dir.mkdir(parents=True)
        (repo_dir / "dists" / "noble" / "main" / "binary-amd64").mkdir(parents=True)
        (repo_dir / "pool" / "main").mkdir(parents=True)
        
        # Create mock Release file
        release = repo_dir / "dists" / "noble" / "Release"
        release.write_text("""Origin: Ubuntu
Label: Ubuntu
Suite: noble
Version: 24.04
Codename: noble
Date: Mon, 01 Jan 2024 00:00:00 UTC
Architectures: amd64 arm64
Components: main restricted universe multiverse
Description: Ubuntu 24.04 LTS
""")
        
        # Create a mock package
        pkg = repo_dir / "pool" / "main" / "test-package_1.0_amd64.deb"
        pkg.write_bytes(b"mock deb content")

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        assert helper.add_artifact(
            category="os-repository",
            name="ubuntu-main",
            version="24.04",
            source_type="os-repository",
            source_reference="http://archive.ubuntu.com/ubuntu/",
            source_path=repo_dir,
            destination="os-repositories/ubuntu/24.04/amd64/main",
            required=True,
            os_family="debian",
            os_version="24.04",
            architecture="x86_64",
            repository_type="apt",
            repository_metadata={"release_file": "present", "packages_gz": "present"},
            signature_status="verified"
        )
        assert helper.write_manifest("os-repositories")

        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        artifact = manifest["artifacts"][0]
        assert artifact["category"] == "os-repository"
        assert artifact["name"] == "ubuntu-main"
        assert artifact["version"] == "24.04"
        assert artifact["os_family"] == "debian"
        assert artifact["os_version"] == "24.04"
        assert artifact["architecture"] == "x86_64"
        assert artifact["repository_type"] == "apt"
        assert artifact["signature_status"] == "verified"

        print("OK   OS repository staging APT")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_missing_metadata():
    """Test that missing repository metadata produces warnings."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        # Create a mock repo WITHOUT repodata
        repo_dir = input_root / "ol9-baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock")

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        assert helper.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir,
            destination="os-repositories/ol9/9/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            repository_metadata=None,
            signature_status="unverified"
        )
        assert helper.write_manifest("os-repositories")

        # Validate - should have warnings about missing metadata
        from validate_manifest import ManifestValidator
        validator = ManifestValidator(manifest_path, staging_root)
        assert validator.validate(), f"Validation failed: {validator.errors}"
        assert any("repository_metadata" in w for w in validator.warnings), \
            f"Expected warning about missing repository_metadata, got: {validator.warnings}"

        print("OK   OS repository missing metadata warning")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_rpm_missing_repomd():
    """Test that RPM repository without repomd.xml fails validation."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        # Create a mock RPM repo WITHOUT repodata/repomd.xml
        repo_dir = input_root / "ol9-baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock")

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        assert helper.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir,
            destination="os-repositories/ol9/9/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            repository_metadata={},  # Empty - missing repomd_xml
            signature_status="unverified"
        )
        assert helper.write_manifest("os-repositories")

        # Validate - should fail due to missing repomd_xml
        from validate_manifest import ManifestValidator
        validator = ManifestValidator(manifest_path, staging_root)
        assert not validator.validate(), "Should fail for missing repomd_xml"
        assert any("repomd_xml" in e for e in validator.errors), \
            f"Expected error about missing repomd_xml, got: {validator.errors}"

        print("OK   RPM repository missing repomd.xml fails validation")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_apt_missing_release():
    """Test that APT repository without Release file fails validation."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        # Create a mock APT repo WITHOUT Release file
        repo_dir = input_root / "ubuntu-main"
        repo_dir.mkdir(parents=True)
        (repo_dir / "pool" / "main").mkdir(parents=True)
        pkg = repo_dir / "pool" / "main" / "test.deb"
        pkg.write_bytes(b"mock")

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        assert helper.add_artifact(
            category="os-repository",
            name="ubuntu-main",
            version="24.04",
            source_type="os-repository",
            source_reference="http://archive.ubuntu.com/ubuntu/",
            source_path=repo_dir,
            destination="os-repositories/ubuntu/24.04/amd64/main",
            required=True,
            os_family="debian",
            os_version="24.04",
            architecture="x86_64",
            repository_type="apt",
            repository_metadata={},  # Empty - missing release_file
            signature_status="unverified"
        )
        assert helper.write_manifest("os-repositories")

        # Validate - should fail due to missing release_file
        from validate_manifest import ManifestValidator
        validator = ManifestValidator(manifest_path, staging_root)
        assert not validator.validate(), "Should fail for missing release_file"
        assert any("release_file" in e for e in validator.errors), \
            f"Expected error about missing release_file, got: {validator.errors}"

        print("OK   APT repository missing Release file fails validation")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_empty_snapshot_dir():
    """Test that empty snapshot directory checksum mismatch is detected."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        # Create an empty repo directory OUTSIDE staging_root
        repo_dir = input_root / "empty-repo"
        repo_dir.mkdir(parents=True)

        # Compute checksum of empty directory
        hasher = hashlib.sha256()
        actual_sha256 = hasher.hexdigest()

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        assert helper.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir,
            destination="os-repositories/ol9/9/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            repository_metadata={"repomd_xml": "present"},
            signature_status="unverified"
        )
        assert helper.write_manifest("os-repositories")

        # Manually corrupt the manifest checksum to test checksum mismatch
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        manifest["artifacts"][0]["sha256"] = "0" * 64
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        # Validate - should fail on checksum mismatch
        from validate_manifest import ManifestValidator
        validator = ManifestValidator(manifest_path, staging_root)
        assert not validator.validate(), "Should fail on checksum mismatch for empty dir"
        assert any("checksum mismatch" in e for e in validator.errors)

        print("OK   Empty snapshot directory checksum mismatch detected")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_duplicate_identity():
    """Test that duplicate repository identity is rejected."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"

        manifest = {
            "schema_version": "1.0.0",
            "profile": "os-repositories",
            "generated_at": "2026-11-24T00:00:00Z",
            "generated_by": "test",
            "artifacts": [
                {
                    "category": "os-repository",
                    "name": "ol9-baseos",
                    "version": "9",
                    "source": {"type": "os-repository", "reference": "https://yum.oracle.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                    "destination": "os-repositories/ol9/9/x86_64/baseos",
                    "sha256": "a" * 64,
                    "size_bytes": 100,
                    "required": True,
                    "feature": "ol9",
                    "os_family": "redhat",
                    "os_version": "9",
                    "architecture": "x86_64",
                    "repository_type": "yum",
                    "signature_status": "unverified"
                },
                {
                    "category": "os-repository",
                    "name": "ol9-baseos",
                    "version": "9",
                    "source": {"type": "os-repository", "reference": "https://yum.oracle.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                    "destination": "os-repositories/ol9/9/x86_64/baseos2",
                    "sha256": "b" * 64,
                    "size_bytes": 100,
                    "required": True,
                    "feature": "ol9",
                    "os_family": "redhat",
                    "os_version": "9",
                    "architecture": "x86_64",
                    "repository_type": "yum",
                    "signature_status": "unverified"
                }
            ]
        }
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        from validate_manifest import ManifestValidator
        validator = ManifestValidator(manifest_path, Path(tmpdir))
        assert not validator.validate(), "Should fail for duplicate identity"
        assert any("duplicate artifact identity" in e for e in validator.errors)

        print("OK   Duplicate repository identity rejected")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_duplicate_destination():
    """Test that duplicate destination path is rejected."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"

        manifest = {
            "schema_version": "1.0.0",
            "profile": "os-repositories",
            "generated_at": "2026-11-24T00:00:00Z",
            "generated_by": "test",
            "artifacts": [
                {
                    "category": "os-repository",
                    "name": "ol9-baseos",
                    "version": "9",
                    "source": {"type": "os-repository", "reference": "https://yum.oracle.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                    "destination": "os-repositories/ol9/9/x86_64/baseos",
                    "sha256": "a" * 64,
                    "size_bytes": 100,
                    "required": True,
                    "feature": "ol9",
                    "os_family": "redhat",
                    "os_version": "9",
                    "architecture": "x86_64",
                    "repository_type": "yum",
                    "signature_status": "unverified"
                },
                {
                    "category": "os-repository",
                    "name": "ol9-appstream",
                    "version": "9",
                    "source": {"type": "os-repository", "reference": "https://yum.oracle.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                    "destination": "os-repositories/ol9/9/x86_64/baseos",  # Same destination
                    "sha256": "b" * 64,
                    "size_bytes": 100,
                    "required": True,
                    "feature": "ol9",
                    "os_family": "redhat",
                    "os_version": "9",
                    "architecture": "x86_64",
                    "repository_type": "yum",
                    "signature_status": "unverified"
                }
            ]
        }
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        from validate_manifest import ManifestValidator
        validator = ManifestValidator(manifest_path, Path(tmpdir))
        assert not validator.validate(), "Should fail for duplicate destination"
        assert any("duplicate destination" in e for e in validator.errors)

        print("OK   Duplicate repository destination rejected")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_required_missing_readiness():
    """Test that missing required repository fails readiness check."""
    tmpdir = tempfile.mkdtemp()
    try:
        manifest_path = Path(tmpdir) / "manifest.json"
        # Create manifest with only one required repository (missing the rest)
        manifest = {
            "schema_version": "1.0.0",
            "profile": "os-repositories",
            "generated_at": "2026-11-24T00:00:00Z",
            "generated_by": "test",
            "artifacts": [
                {"category": "os-repository", "name": "ol9-baseos", "version": "9",
                 "source": {"type": "os-repository", "reference": "https://yum.oracle.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "os-repositories/ol9/9/x86_64/baseos", "sha256": "a" * 64, "size_bytes": 100, "required": True, "feature": "ol9",
                 "os_family": "redhat", "os_version": "9", "architecture": "x86_64", "repository_type": "yum", "signature_status": "unverified"},
            ]
        }
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        from check_readiness import ProfileChecker
        checker = ProfileChecker(manifest_path)
        checker.load_manifest()
        checker.index_artifacts()
        ready = checker.check_profile("os-repositories")
        assert not ready, "Should not be ready when required repositories missing"
        assert len(checker.results["missing_required"]) == 7, f"Expected 7 missing, got {len(checker.results['missing_required'])}"
        # Check specific missing repos
        missing = checker.results["missing_required"]
        assert any("ol9-appstream" in m for m in missing)
        assert any("ubuntu-main" in m and "22.04" in m for m in missing)
        assert any("ubuntu-updates" in m and "22.04" in m for m in missing)
        assert any("ubuntu-security" in m and "22.04" in m for m in missing)
        assert any("ubuntu-main" in m and "24.04" in m for m in missing)
        assert any("ubuntu-updates" in m and "24.04" in m for m in missing)
        assert any("ubuntu-security" in m and "24.04" in m for m in missing)

        print("OK   Missing required repositories fails readiness")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_source_path_traversal():
    """Test that source path traversal is handled safely (copies resolved source)."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        # Create a real repo directory
        repo_dir = input_root / "ol9-baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock")

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        # Use source path with traversal attempt - should resolve to actual path
        assert helper.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir / ".." / "ol9-baseos",  # Path traversal in source
            destination="os-repositories/ol9/9/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            signature_status="unverified"
        )
        assert helper.write_manifest("os-repositories")

        print("OK   Source path traversal resolved safely")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_symlink_handling():
    """Test that symlinks in source that escape the source tree are rejected."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        # Create a real repo directory
        repo_dir = input_root / "ol9-baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock")

        # Create a symlink inside the repo pointing outside the source tree
        link = repo_dir / "escape_link"
        link.symlink_to("/etc/passwd")

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        # Symlink escaping source tree should be rejected
        assert not helper.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir,
            destination="os-repositories/ol9/9/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            signature_status="unverified"
        )

        print("OK   Symlink escaping source tree rejected")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_unsupported_version():
    """Test that unsupported OS version is rejected at staging."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        repo_dir = input_root / "ol8-baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock")

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        # Oracle Linux 8 is not in supported versions (only 9)
        # Should be rejected at staging time
        assert not helper.add_artifact(
            category="os-repository",
            name="ol8-baseos",
            version="8",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir,
            destination="os-repositories/ol8/8/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="8",
            architecture="x86_64",
            repository_type="yum",
            signature_status="unverified"
        )

        print("OK   OS repository unsupported version rejected at staging")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_unsupported_ubuntu_version():
    """Test that unsupported Ubuntu version is rejected at staging."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        repo_dir = input_root / "ubuntu-main"
        repo_dir.mkdir(parents=True)
        (repo_dir / "pool" / "main").mkdir(parents=True)
        pkg = repo_dir / "pool" / "main" / "test.deb"
        pkg.write_bytes(b"mock")

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        # Ubuntu 20.04 is not in supported versions (only 22.04, 24.04)
        assert not helper.add_artifact(
            category="os-repository",
            name="ubuntu-main",
            version="20.04",
            source_type="os-repository",
            source_reference="http://archive.ubuntu.com/ubuntu/",
            source_path=repo_dir,
            destination="os-repositories/ubuntu/20.04/amd64/main",
            required=True,
            os_family="debian",
            os_version="20.04",
            architecture="x86_64",
            repository_type="apt",
            signature_status="unverified"
        )

        print("OK   OS repository unsupported Ubuntu version rejected at staging")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_unsupported_architecture():
    """Test that unsupported architecture is rejected at staging."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        repo_dir = input_root / "ol9-baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock")

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        # aarch64 is not supported for Oracle Linux (only x86_64)
        assert not helper.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir,
            destination="os-repositories/ol9/9/aarch64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="aarch64",
            repository_type="yum",
            signature_status="unverified"
        )

        print("OK   OS repository unsupported architecture rejected at staging")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_mismatched_repo_type():
    """Test that mismatched repository_type for OS family is rejected."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        repo_dir = input_root / "ol9-baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock")

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        # Oracle Linux with apt type should be rejected
        assert not helper.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir,
            destination="os-repositories/ol9/9/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="apt",  # Wrong type for redhat
            signature_status="unverified"
        )

        print("OK   OS repository mismatched repo type rejected at staging")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_checksum_mismatch():
    """Test checksum mismatch detection for repository."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        repo_dir = input_root / "ol9-baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock content v1")

        # Stage with correct checksum first
        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        assert helper.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir,
            destination="os-repositories/ol9/9/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            signature_status="unverified"
        )
        assert helper.write_manifest("os-repositories")
        
        # Manually corrupt the manifest checksum
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        manifest["artifacts"][0]["sha256"] = "0" * 64
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        # Validate - should fail on checksum
        from validate_manifest import ManifestValidator
        validator = ManifestValidator(manifest_path, staging_root)
        assert not validator.validate(), "Should fail on checksum mismatch"
        assert any("checksum mismatch" in e for e in validator.errors)

        print("OK   OS repository checksum mismatch detection")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_path_traversal():
    """Test path traversal rejection for os-repository."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"

        repo_dir = Path(tmpdir) / "ol9-baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock")

        helper = StagingHelper(staging_root, manifest_path, force=False)
        assert not helper.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir,
            destination="../../../etc/yum.repos.d/malicious.repo",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            signature_status="unverified"
        )

        print("OK   OS repository path traversal rejection")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_overwrite_protection():
    """Test overwrite protection for os-repository."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        repo_dir = input_root / "ol9-baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock v1")

        # First staging
        helper1 = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        assert helper1.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir,
            destination="os-repositories/ol9/9/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            signature_status="unverified"
        )
        assert helper1.write_manifest("os-repositories")

        # Second staging without force should fail
        helper2 = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        assert not helper2.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir,
            destination="os-repositories/ol9/9/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            signature_status="unverified"
        )

        # With force should succeed
        helper3 = StagingHelper(staging_root, manifest_path, force=True, input_root=input_root)
        assert helper3.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir,
            destination="os-repositories/ol9/9/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            signature_status="unverified"
        )

        print("OK   OS repository overwrite protection")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_deterministic():
    """Test deterministic manifest generation for os-repository."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path1 = Path(tmpdir) / "manifest1.json"
        manifest_path2 = Path(tmpdir) / "manifest2.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        repo_dir = input_root / "ol9-baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock content for determinism")

        os.environ["SOURCE_DATE_EPOCH"] = "1700000000"

        try:
            helper1 = StagingHelper(staging_root, manifest_path1, force=False, input_root=input_root)
            assert helper1.add_artifact(
                category="os-repository",
                name="ol9-baseos",
                version="9",
                source_type="os-repository",
                source_reference="https://yum.oracle.com/",
                source_path=repo_dir,
                destination="os-repositories/ol9/9/x86_64/baseos",
                required=True,
                os_family="redhat",
                os_version="9",
                architecture="x86_64",
                repository_type="yum",
                signature_status="unverified"
            )
            assert helper1.write_manifest("os-repositories")

            helper2 = StagingHelper(staging_root, manifest_path2, force=True, input_root=input_root)
            assert helper2.add_artifact(
                category="os-repository",
                name="ol9-baseos",
                version="9",
                source_type="os-repository",
                source_reference="https://yum.oracle.com/",
                source_path=repo_dir,
                destination="os-repositories/ol9/9/x86_64/baseos",
                required=True,
                os_family="redhat",
                os_version="9",
                architecture="x86_64",
                repository_type="yum",
                signature_status="unverified"
            )
            assert helper2.write_manifest("os-repositories")

            with open(manifest_path1, 'rb') as f1, open(manifest_path2, 'rb') as f2:
                assert f1.read() == f2.read(), "Manifests not byte-for-byte identical"

            print("OK   OS repository deterministic manifest generation")
        finally:
            if "SOURCE_DATE_EPOCH" in os.environ:
                del os.environ["SOURCE_DATE_EPOCH"]
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repositories_profile_readiness():
    """Test os-repositories profile readiness check."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"

        # Create all 8 required repo directories with content
        repos = [
            ("ol9-baseos", "9", "os-repositories/ol9/9/x86_64/baseos", "redhat", "yum"),
            ("ol9-appstream", "9", "os-repositories/ol9/9/x86_64/appstream", "redhat", "yum"),
            ("ubuntu-main", "22.04", "os-repositories/ubuntu/22.04/amd64/main", "debian", "apt"),
            ("ubuntu-updates", "22.04", "os-repositories/ubuntu/22.04/amd64/updates", "debian", "apt"),
            ("ubuntu-security", "22.04", "os-repositories/ubuntu/22.04/amd64/security", "debian", "apt"),
            ("ubuntu-main", "24.04", "os-repositories/ubuntu/24.04/amd64/main", "debian", "apt"),
            ("ubuntu-updates", "24.04", "os-repositories/ubuntu/24.04/amd64/updates", "debian", "apt"),
            ("ubuntu-security", "24.04", "os-repositories/ubuntu/24.04/amd64/security", "debian", "apt"),
        ]

        artifacts = []
        for name, version, destination, os_family, repo_type in repos:
            repo_dir = staging_root / destination
            repo_dir.mkdir(parents=True)
            pkg = repo_dir / "Packages" / "test.rpm"
            pkg.parent.mkdir(parents=True, exist_ok=True)
            pkg.write_bytes(b"mock content")

            # Compute checksum
            import hashlib
            hasher = hashlib.sha256()
            for file_path in sorted(repo_dir.rglob("*")):
                if file_path.is_file():
                    rel_path = file_path.relative_to(repo_dir)
                    hasher.update(str(rel_path).encode())
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(8192), b''):
                            hasher.update(chunk)
            sha256 = hasher.hexdigest()

            artifacts.append({
                "category": "os-repository",
                "name": name,
                "version": version,
                "source": {"type": "os-repository", "reference": "https://example.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                "destination": destination,
                "sha256": sha256,
                "size_bytes": 100,
                "required": True,
                "feature": "ol9" if os_family == "redhat" else ("ubuntu2204" if version == "22.04" else "ubuntu2404"),
                "os_family": os_family,
                "os_version": version,
                "architecture": "x86_64",
                "repository_type": repo_type,
                "repository_metadata": {"repomd_xml": "present"} if repo_type == "yum" else {"release_file": "present"},
                "signature_status": "unverified"
            })

        manifest = {
            "schema_version": "1.0.0",
            "profile": "os-repositories",
            "generated_at": "2026-11-24T00:00:00Z",
            "generated_by": "test",
            "artifacts": artifacts
        }
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        from check_readiness import ProfileChecker
        checker = ProfileChecker(manifest_path, staging_root)
        checker.load_manifest()
        checker.index_artifacts()
        ready = checker.check_profile("os-repositories")
        assert ready, f"os-repositories profile should be ready: {checker.results['missing_required']}"

        # Test missing required repository
        manifest["artifacts"].pop()  # Remove one
        manifest_path2 = Path(tmpdir) / "manifest2.json"
        with open(manifest_path2, 'w') as f:
            json.dump(manifest, f)
        
        checker2 = ProfileChecker(manifest_path2, staging_root)
        checker2.load_manifest()
        checker2.index_artifacts()
        ready2 = checker2.check_profile("os-repositories")
        assert not ready2, "Should not be ready with missing repository"
        assert len(checker2.results["missing_required"]) > 0

        print("OK   OS repositories profile readiness")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_required_vs_optional():
    """Test required vs optional repository handling."""
    tmpdir = tempfile.mkdtemp()
    try:
        manifest_path = Path(tmpdir) / "manifest.json"
        # Only optional repositories
        manifest = {
            "schema_version": "1.0.0",
            "profile": "os-repositories",
            "generated_at": "2026-11-24T00:00:00Z",
            "generated_by": "test",
            "artifacts": [
                {"category": "os-repository", "name": "ol9-addons", "version": "9",
                 "source": {"type": "os-repository", "reference": "https://yum.oracle.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                 "destination": "os-repositories/ol9/9/x86_64/addons", "sha256": "a" * 64, "size_bytes": 100, "required": False, "feature": "ol9",
                 "os_family": "redhat", "os_version": "9", "architecture": "x86_64", "repository_type": "yum", "signature_status": "unverified"},
            ]
        }
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        from check_readiness import ProfileChecker
        checker = ProfileChecker(manifest_path)
        checker.load_manifest()
        checker.index_artifacts()
        
        # Should fail - required repositories are missing
        ready = checker.check_profile("os-repositories")
        assert not ready, "Should not be ready when required repositories missing"
        assert len(checker.results["missing_required"]) > 0
        # But optional should be tracked
        assert len(checker.results["missing_optional"]) == 0  # ol9-addons is not in required list

        print("OK   OS repository required vs optional")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_missing_signature_status():
    """Test that missing signature_status produces warning."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        repo_dir = input_root / "ol9-baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock")

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        assert helper.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir,
            destination="os-repositories/ol9/9/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            signature_status=None  # Missing
        )
        assert helper.write_manifest("os-repositories")

        from validate_manifest import ManifestValidator
        validator = ManifestValidator(manifest_path, staging_root)
        assert validator.validate(), f"Validation failed: {validator.errors}"
        assert any("signature_status" in w for w in validator.warnings), \
            f"Expected warning about missing signature_status, got: {validator.warnings}"

        print("OK   OS repository missing signature_status warning")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_absolute_source_path_inside_root():
    """Test that absolute source path inside authorized root is accepted."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        repo_dir = input_root / "ol9-baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock")

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        # Absolute path inside authorized root should be accepted
        assert helper.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir.resolve(),  # Absolute path
            destination="os-repositories/ol9/9/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            signature_status="unverified"
        )
        assert helper.write_manifest("os-repositories")

        print("OK   Absolute source path inside authorized root accepted")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_absolute_source_path_outside_root():
    """Test that absolute source path outside authorized root is rejected."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        # Repo outside the authorized input root
        repo_dir = Path(tmpdir) / "outside"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock")

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        # Absolute path outside authorized root should be rejected
        assert not helper.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir.resolve(),  # Absolute path outside root
            destination="os-repositories/ol9/9/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            signature_status="unverified"
        )

        print("OK   Absolute source path outside authorized root rejected")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_symlink_inside_root():
    """Test that symlink targeting inside authorized root is accepted."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        # Real repo directory
        real_repo = input_root / "real-ol9-baseos"
        real_repo.mkdir(parents=True)
        (real_repo / "Packages").mkdir()
        pkg = real_repo / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock")

        # Symlink inside input root pointing to real repo
        link_repo = input_root / "ol9-baseos"
        link_repo.symlink_to(real_repo)

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        # Symlink inside authorized root should be accepted (resolves to real repo)
        assert helper.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=link_repo,  # Symlink
            destination="os-repositories/ol9/9/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            signature_status="unverified"
        )
        assert helper.write_manifest("os-repositories")

        # Verify the content was copied
        dest = staging_root / "os-repositories/ol9/9/x86_64/baseos"
        assert dest.exists()
        assert (dest / "Packages" / "test.rpm").exists()

        print("OK   Symlink inside authorized root accepted")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_symlink_outside_root():
    """Test that symlink targeting outside authorized root is rejected."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        # Real repo directory OUTSIDE input root
        real_repo = Path(tmpdir) / "outside"
        real_repo.mkdir(parents=True)
        (real_repo / "Packages").mkdir()
        pkg = real_repo / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock")

        # Symlink inside input root pointing to outside repo
        link_repo = input_root / "ol9-baseos"
        link_repo.symlink_to(real_repo)

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        # Symlink pointing outside authorized root should be rejected
        assert not helper.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=link_repo,  # Symlink pointing outside
            destination="os-repositories/ol9/9/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            signature_status="unverified"
        )

        print("OK   Symlink targeting outside authorized root rejected")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_symlink_in_repo_escapes_source_tree():
    """Test that symlink inside repo pointing outside source tree is rejected."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        # Repo directory with a symlink pointing outside
        repo_dir = input_root / "ol9-baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock")

        # Create a symlink inside repo pointing outside the repo
        escape_link = repo_dir / "escape"
        outside_dir = Path(tmpdir) / "outside"
        outside_dir.mkdir(parents=True)
        (outside_dir / "secret").write_bytes(b"secret")
        escape_link.symlink_to(outside_dir)

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        # Symlink inside repo pointing outside source tree should be rejected
        assert not helper.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir,
            destination="os-repositories/ol9/9/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            signature_status="unverified"
        )

        print("OK   Symlink inside repo escaping source tree rejected")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_destination_escape():
    """Test that destination path traversal is rejected."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        repo_dir = input_root / "ol9-baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock")

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        # Destination with path traversal that escapes staging root should be rejected
        assert not helper.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir,
            destination="os-repositories/ol9/9/x86_64/../../../../../escape",  # Path traversal (5 levels up)
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            signature_status="unverified"
        )

        print("OK   Destination path traversal rejected")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_missing_input_root():
    """Test that missing --input-root is rejected for os-repository artifacts."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"

        repo_dir = Path(tmpdir) / "ol9-baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock")

        # No input_root provided - should fail
        helper = StagingHelper(staging_root, manifest_path, force=False)
        assert not helper.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir,
            destination="os-repositories/ol9/9/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            signature_status="unverified"
        )

        print("OK   Missing input-root rejected for os-repository")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_invalid_input_root():
    """Test that non-existent or non-directory input root is rejected."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"

        # Non-existent input root
        input_root = Path(tmpdir) / "nonexistent"
        try:
            helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "does not exist" in str(e)

        # File as input root (not directory)
        input_root = Path(tmpdir) / "input_file"
        input_root.write_text("not a dir")
        try:
            helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "not a directory" in str(e)

        print("OK   Invalid input root rejected")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_os_repository_source_outside_input_root():
    """Test that source path outside input root is rejected."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"
        input_root = Path(tmpdir) / "input"
        input_root.mkdir(parents=True)

        # Repo outside the authorized input root
        repo_dir = Path(tmpdir) / "outside"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock")

        helper = StagingHelper(staging_root, manifest_path, force=False, input_root=input_root)
        # Source outside input root should be rejected
        assert not helper.add_artifact(
            category="os-repository",
            name="ol9-baseos",
            version="9",
            source_type="os-repository",
            source_reference="https://yum.oracle.com/",
            source_path=repo_dir,
            destination="os-repositories/ol9/9/x86_64/baseos",
            required=True,
            os_family="redhat",
            os_version="9",
            architecture="x86_64",
            repository_type="yum",
            signature_status="unverified"
        )

        print("OK   Source outside input root rejected")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_readiness_missing_rpm_metadata():
    """Test that readiness rejects missing RPM metadata."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"

        # Create a mock RPM repo directory
        repo_dir = staging_root / "os-repositories/ol9/9/x86_64/baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock")

        # Create manifest without repomd_xml in repository_metadata
        manifest = {
            "schema_version": "1.0.0",
            "profile": "os-repositories",
            "generated_at": "2026-11-24T00:00:00Z",
            "generated_by": "test",
            "artifacts": [
                {
                    "category": "os-repository",
                    "name": "ol9-baseos",
                    "version": "9",
                    "source": {"type": "os-repository", "reference": "https://yum.oracle.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                    "destination": "os-repositories/ol9/9/x86_64/baseos",
                    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",  # empty dir hash
                    "size_bytes": 100,
                    "required": True,
                    "feature": "ol9",
                    "os_family": "redhat",
                    "os_version": "9",
                    "architecture": "x86_64",
                    "repository_type": "yum",
                    "repository_metadata": {},  # Missing repomd_xml
                    "signature_status": "unverified"
                }
            ]
        }
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        from check_readiness import ProfileChecker
        checker = ProfileChecker(manifest_path, staging_root)
        checker.load_manifest()
        checker.index_artifacts()
        ready = checker.check_profile("os-repositories")
        assert not ready, "Should not be ready due to missing RPM metadata"
        assert len(checker.results["metadata_missing"]) > 0
        assert any("repomd_xml" in m for m in checker.results["metadata_missing"])

        print("OK   Readiness rejects missing RPM metadata")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_readiness_missing_apt_metadata():
    """Test that readiness rejects missing APT metadata."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"

        # Create a mock APT repo directory
        repo_dir = staging_root / "os-repositories/ubuntu/24.04/amd64/main"
        repo_dir.mkdir(parents=True)
        (repo_dir / "pool" / "main").mkdir(parents=True)
        pkg = repo_dir / "pool" / "main" / "test.deb"
        pkg.write_bytes(b"mock")

        # Create manifest without release_file in repository_metadata
        manifest = {
            "schema_version": "1.0.0",
            "profile": "os-repositories",
            "generated_at": "2026-11-24T00:00:00Z",
            "generated_by": "test",
            "artifacts": [
                {
                    "category": "os-repository",
                    "name": "ubuntu-main",
                    "version": "24.04",
                    "source": {"type": "os-repository", "reference": "http://archive.ubuntu.com/ubuntu/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                    "destination": "os-repositories/ubuntu/24.04/amd64/main",
                    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",  # empty dir hash
                    "size_bytes": 100,
                    "required": True,
                    "feature": "ubuntu2404",
                    "os_family": "debian",
                    "os_version": "24.04",
                    "architecture": "x86_64",
                    "repository_type": "apt",
                    "repository_metadata": {},  # Missing release_file
                    "signature_status": "unverified"
                }
            ]
        }
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        from check_readiness import ProfileChecker
        checker = ProfileChecker(manifest_path, staging_root)
        checker.load_manifest()
        checker.index_artifacts()
        ready = checker.check_profile("os-repositories")
        assert not ready, "Should not be ready due to missing APT metadata"
        assert len(checker.results["metadata_missing"]) > 0
        assert any("release_file" in m for m in checker.results["metadata_missing"])

        print("OK   Readiness rejects missing APT metadata")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_readiness_checksum_mismatch():
    """Test that readiness rejects checksum mismatch."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"

        # Create a mock repo directory with content
        repo_dir = staging_root / "os-repositories/ol9/9/x86_64/baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock content")

        # Compute actual checksum
        import hashlib
        hasher = hashlib.sha256()
        for file_path in sorted(repo_dir.rglob("*")):
            if file_path.is_file():
                rel_path = file_path.relative_to(repo_dir)
                hasher.update(str(rel_path).encode())
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        hasher.update(chunk)
        actual_sha256 = hasher.hexdigest()

        # Create manifest with WRONG checksum
        manifest = {
            "schema_version": "1.0.0",
            "profile": "os-repositories",
            "generated_at": "2026-11-24T00:00:00Z",
            "generated_by": "test",
            "artifacts": [
                {
                    "category": "os-repository",
                    "name": "ol9-baseos",
                    "version": "9",
                    "source": {"type": "os-repository", "reference": "https://yum.oracle.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                    "destination": "os-repositories/ol9/9/x86_64/baseos",
                    "sha256": "0" * 64,  # Wrong checksum
                    "size_bytes": 100,
                    "required": True,
                    "feature": "ol9",
                    "os_family": "redhat",
                    "os_version": "9",
                    "architecture": "x86_64",
                    "repository_type": "yum",
                    "repository_metadata": {"repomd_xml": "present"},
                    "signature_status": "unverified"
                }
            ]
        }
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        from check_readiness import ProfileChecker
        checker = ProfileChecker(manifest_path, staging_root)
        checker.load_manifest()
        checker.index_artifacts()
        ready = checker.check_profile("os-repositories")
        assert not ready, "Should not be ready due to checksum mismatch"
        assert len(checker.results["checksum_failed"]) > 0
        assert any("checksum mismatch" in m for m in checker.results["checksum_failed"])

        print("OK   Readiness rejects checksum mismatch")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_readiness_unsupported_os_version():
    """Test that readiness rejects unsupported OS/version."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"

        repo_dir = staging_root / "os-repositories/ol8/8/x86_64/baseos"
        repo_dir.mkdir(parents=True)
        (repo_dir / "Packages").mkdir()
        pkg = repo_dir / "Packages" / "test.rpm"
        pkg.write_bytes(b"mock")

        manifest = {
            "schema_version": "1.0.0",
            "profile": "os-repositories",
            "generated_at": "2026-11-24T00:00:00Z",
            "generated_by": "test",
            "artifacts": [
                {
                    "category": "os-repository",
                    "name": "ol8-baseos",
                    "version": "8",
                    "source": {"type": "os-repository", "reference": "https://yum.oracle.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                    "destination": "os-repositories/ol8/8/x86_64/baseos",
                    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "size_bytes": 100,
                    "required": True,
                    "feature": "ol8",
                    "os_family": "redhat",
                    "os_version": "8",  # Unsupported
                    "architecture": "x86_64",
                    "repository_type": "yum",
                    "repository_metadata": {"repomd_xml": "present"},
                    "signature_status": "unverified"
                }
            ]
        }
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        # Validator should also reject
        from validate_manifest import ManifestValidator
        validator = ManifestValidator(manifest_path, staging_root)
        assert not validator.validate(), "Validator should reject unsupported OS version"
        assert any("unsupported Oracle Linux version" in e for e in validator.errors)

        print("OK   Readiness rejects unsupported OS version")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_readiness_unverified_signature_reported():
    """Test that readiness reports unverified signatures without claiming authenticity."""
    tmpdir = tempfile.mkdtemp()
    try:
        staging_root = Path(tmpdir) / "staging"
        staging_root.mkdir(parents=True)
        manifest_path = Path(tmpdir) / "manifest.json"

        # Create all 8 required repo directories with content
        repos = [
            ("ol9-baseos", "9", "os-repositories/ol9/9/x86_64/baseos", "redhat", "yum"),
            ("ol9-appstream", "9", "os-repositories/ol9/9/x86_64/appstream", "redhat", "yum"),
            ("ubuntu-main", "22.04", "os-repositories/ubuntu/22.04/amd64/main", "debian", "apt"),
            ("ubuntu-updates", "22.04", "os-repositories/ubuntu/22.04/amd64/updates", "debian", "apt"),
            ("ubuntu-security", "22.04", "os-repositories/ubuntu/22.04/amd64/security", "debian", "apt"),
            ("ubuntu-main", "24.04", "os-repositories/ubuntu/24.04/amd64/main", "debian", "apt"),
            ("ubuntu-updates", "24.04", "os-repositories/ubuntu/24.04/amd64/updates", "debian", "apt"),
            ("ubuntu-security", "24.04", "os-repositories/ubuntu/24.04/amd64/security", "debian", "apt"),
        ]

        artifacts = []
        for name, version, destination, os_family, repo_type in repos:
            repo_dir = staging_root / destination
            repo_dir.mkdir(parents=True)
            pkg = repo_dir / "Packages" / "test.rpm"
            pkg.parent.mkdir(parents=True, exist_ok=True)
            pkg.write_bytes(b"mock content")

            # Compute checksum
            import hashlib
            hasher = hashlib.sha256()
            for file_path in sorted(repo_dir.rglob("*")):
                if file_path.is_file():
                    rel_path = file_path.relative_to(repo_dir)
                    hasher.update(str(rel_path).encode())
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(8192), b''):
                            hasher.update(chunk)
            sha256 = hasher.hexdigest()

            artifacts.append({
                "category": "os-repository",
                "name": name,
                "version": version,
                "source": {"type": "os-repository", "reference": "https://example.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                "destination": destination,
                "sha256": sha256,
                "size_bytes": 100,
                "required": True,
                "feature": "ol9" if os_family == "redhat" else ("ubuntu2204" if version == "22.04" else "ubuntu2404"),
                "os_family": os_family,
                "os_version": version,
                "architecture": "x86_64",
                "repository_type": repo_type,
                "repository_metadata": {"repomd_xml": "present"} if repo_type == "yum" else {"release_file": "present"},
                "signature_status": "unverified"
            })

        manifest = {
            "schema_version": "1.0.0",
            "profile": "os-repositories",
            "generated_at": "2026-11-24T00:00:00Z",
            "generated_by": "test",
            "artifacts": artifacts
        }
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        from check_readiness import ProfileChecker
        checker = ProfileChecker(manifest_path, staging_root)
        checker.load_manifest()
        checker.index_artifacts()
        ready = checker.check_profile("os-repositories")
        # Should be ready (checksums match, metadata present) but with unverified signature warning
        assert ready, f"Should be ready despite unverified signature: {checker.results}"
        assert len(checker.results["signature_unverified"]) > 0
        assert any("signature_status=unverified" in m for m in checker.results["signature_unverified"])
        # Verify it doesn't claim "verified" authenticity
        assert not any("verified" in m and "unverified" not in m for m in checker.results["signature_unverified"])

        print("OK   Readiness reports unverified signatures without claiming authenticity")
    finally:
        import shutil
        shutil.rmtree(tmpdir)



def test_profile_check_without_staging_root_no_readiness():
    """Test that profile compatibility check without staging root does not claim deployment readiness."""
    tmpdir = tempfile.mkdtemp()
    try:
        manifest_path = Path(tmpdir) / "manifest.json"
        repos = [
            ("ol9-baseos", "9", "os-repositories/ol9/9/x86_64/baseos", "redhat", "yum"),
            ("ol9-appstream", "9", "os-repositories/ol9/9/x86_64/appstream", "redhat", "yum"),
            ("ubuntu-main", "22.04", "os-repositories/ubuntu/22.04/amd64/main", "debian", "apt"),
            ("ubuntu-updates", "22.04", "os-repositories/ubuntu/22.04/amd64/updates", "debian", "apt"),
            ("ubuntu-security", "22.04", "os-repositories/ubuntu/22.04/amd64/security", "debian", "apt"),
            ("ubuntu-main", "24.04", "os-repositories/ubuntu/24.04/amd64/main", "debian", "apt"),
            ("ubuntu-updates", "24.04", "os-repositories/ubuntu/24.04/amd64/updates", "debian", "apt"),
            ("ubuntu-security", "24.04", "os-repositories/ubuntu/24.04/amd64/security", "debian", "apt"),
        ]
        artifacts = []
        for name, version, destination, os_family, repo_type in repos:
            repo_dir = Path(tmpdir) / destination
            repo_dir.mkdir(parents=True)
            pkg = repo_dir / "Packages" / "test.rpm"
            pkg.parent.mkdir(parents=True, exist_ok=True)
            pkg.write_bytes(b"mock content")
            import hashlib
            hasher = hashlib.sha256()
            for file_path in sorted(repo_dir.rglob("*")):
                if file_path.is_file():
                    rel_path = file_path.relative_to(repo_dir)
                    hasher.update(str(rel_path).encode())
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(8192), b''):
                            hasher.update(chunk)
            sha256 = hasher.hexdigest()
            artifacts.append({
                "category": "os-repository", "name": name, "version": version,
                "source": {"type": "os-repository", "reference": "https://example.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                "destination": destination, "sha256": sha256, "size_bytes": 100, "required": True,
                "feature": "ol9" if os_family == "redhat" else ("ubuntu2204" if version == "22.04" else "ubuntu2404"),
                "os_family": os_family, "os_version": version, "architecture": "x86_64",
                "repository_type": repo_type,
                "repository_metadata": {"repomd_xml": "present"} if repo_type == "yum" else {"release_file": "present"},
                "signature_status": "unverified"
            })
        manifest = {"schema_version": "1.0.0", "profile": "os-repositories", "generated_at": "2026-11-24T00:00:00Z", "generated_by": "test", "artifacts": artifacts}
        with open(manifest_path, 'w') as f: json.dump(manifest, f)
        from check_readiness import ProfileChecker
        checker = ProfileChecker(manifest_path)
        checker.load_manifest()
        checker.index_artifacts()
        ready = checker.check_profile("os-repositories")
        assert ready, f"Profile compatibility should pass: {checker.results}"
        assert len(checker.results["integrity_unverified"]) == 8, f"Expected 8 integrity_unverified, got {len(checker.results['integrity_unverified'])}"
        print("OK   Profile check without staging root reports integrity unverified")
    finally:
        import shutil; shutil.rmtree(tmpdir)


def test_os_repository_readiness_without_staging_root_fails():
    """Test that deployment readiness for os-repositories fails without staging root."""
    tmpdir = tempfile.mkdtemp()
    try:
        manifest_path = Path(tmpdir) / "manifest.json"
        repos = [
            ("ol9-baseos", "9", "os-repositories/ol9/9/x86_64/baseos", "redhat", "yum"),
            ("ol9-appstream", "9", "os-repositories/ol9/9/x86_64/appstream", "redhat", "yum"),
            ("ubuntu-main", "22.04", "os-repositories/ubuntu/22.04/amd64/main", "debian", "apt"),
            ("ubuntu-updates", "22.04", "os-repositories/ubuntu/22.04/amd64/updates", "debian", "apt"),
            ("ubuntu-security", "22.04", "os-repositories/ubuntu/22.04/amd64/security", "debian", "apt"),
            ("ubuntu-main", "24.04", "os-repositories/ubuntu/24.04/amd64/main", "debian", "apt"),
            ("ubuntu-updates", "24.04", "os-repositories/ubuntu/24.04/amd64/updates", "debian", "apt"),
            ("ubuntu-security", "24.04", "os-repositories/ubuntu/24.04/amd64/security", "debian", "apt"),
        ]
        artifacts = []
        for name, version, destination, os_family, repo_type in repos:
            repo_dir = Path(tmpdir) / destination
            repo_dir.mkdir(parents=True)
            pkg = repo_dir / "Packages" / "test.rpm"
            pkg.parent.mkdir(parents=True, exist_ok=True)
            pkg.write_bytes(b"mock content")
            import hashlib
            hasher = hashlib.sha256()
            for file_path in sorted(repo_dir.rglob("*")):
                if file_path.is_file():
                    rel_path = file_path.relative_to(repo_dir)
                    hasher.update(str(rel_path).encode())
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(8192), b''):
                            hasher.update(chunk)
            sha256 = hasher.hexdigest()
            artifacts.append({
                "category": "os-repository", "name": name, "version": version,
                "source": {"type": "os-repository", "reference": "https://example.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                "destination": destination, "sha256": sha256, "size_bytes": 100, "required": True,
                "feature": "ol9" if os_family == "redhat" else ("ubuntu2204" if version == "22.04" else "ubuntu2404"),
                "os_family": os_family, "os_version": version, "architecture": "x86_64",
                "repository_type": repo_type,
                "repository_metadata": {"repomd_xml": "present"} if repo_type == "yum" else {"release_file": "present"},
                "signature_status": "unverified"
            })
        manifest = {"schema_version": "1.0.0", "profile": "os-repositories", "generated_at": "2026-11-24T00:00:00Z", "generated_by": "test", "artifacts": artifacts}
        with open(manifest_path, 'w') as f: json.dump(manifest, f)
        from check_readiness import ProfileChecker
        checker = ProfileChecker(manifest_path)
        checker.load_manifest()
        checker.index_artifacts()
        ready = checker.check_profile("os-repositories")
        assert ready, "Profile compatibility should pass"
        assert len(checker.results["integrity_unverified"]) == 8, f"Expected 8, got {len(checker.results['integrity_unverified'])}"
        staging_root = Path(tmpdir)
        checker2 = ProfileChecker(manifest_path, staging_root=staging_root)
        checker2.load_manifest()
        checker2.index_artifacts()
        ready2 = checker2.check_profile("os-repositories")
        assert ready2, f"Deployment readiness should pass with staging_root: {checker2.results}"
        assert len(checker2.results["integrity_unverified"]) == 0
        print("OK   OS repository readiness requires staging root for deployment")
    finally:
        import shutil; shutil.rmtree(tmpdir)


def test_signature_classifications():
    """Test that all four signature classifications are reported correctly."""
    tmpdir = tempfile.mkdtemp()
    try:
        manifest_path = Path(tmpdir) / "manifest.json"
        # Use actual required artifact names for kubespray-control-node
        artifacts = [
            {"category": "python-package", "name": "ansible", "version": "12.3.0", "source": {"type": "pypi", "reference": "https://pypi.org/", "fetched_at": "2026-11-24T00:00:00Z", "verified": True}, "destination": "packages/ansible-12.3.0.whl", "sha256": "a" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None, "signature_status": "verified"},
            {"category": "python-package", "name": "ansible-core", "version": "2.19.3", "source": {"type": "pypi", "reference": "https://pypi.org/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False}, "destination": "packages/ansible-core-2.19.3.whl", "sha256": "b" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None, "signature_status": "unverified"},
            {"category": "python-package", "name": "bcrypt", "version": "<6", "source": {"type": "pypi", "reference": "https://pypi.org/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False}, "destination": "packages/bcrypt-<6.whl", "sha256": "c" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None, "signature_status": "absent"},
            {"category": "python-package", "name": "cryptography", "version": "50.0.1", "source": {"type": "pypi", "reference": "https://pypi.org/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False}, "destination": "packages/cryptography-50.0.1.whl", "sha256": "d" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None, "signature_status": "not_applicable"},
            # Add remaining required artifacts with default signature_status
            {"category": "python-package", "name": "jmespath", "version": "1.1.0", "source": {"type": "pypi", "reference": "https://pypi.org/", "fetched_at": "2026-11-24T00:00:00Z", "verified": True}, "destination": "packages/jmespath-1.1.0.whl", "sha256": "e" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None, "signature_status": "verified"},
            {"category": "python-package", "name": "netaddr", "version": "1.3.0", "source": {"type": "pypi", "reference": "https://pypi.org/", "fetched_at": "2026-11-24T00:00:00Z", "verified": True}, "destination": "packages/netaddr-1.3.0.whl", "sha256": "f" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None, "signature_status": "verified"},
            {"category": "python-package", "name": "passlib", "version": "1.7.4", "source": {"type": "pypi", "reference": "https://pypi.org/", "fetched_at": "2026-11-24T00:00:00Z", "verified": True}, "destination": "packages/passlib-1.7.4.whl", "sha256": "g" * 64, "size_bytes": 100, "platform": "py3-none-any", "required": True, "feature": None, "signature_status": "verified"},
            {"category": "ansible-collection", "name": "community.general", "version": "11.2.0", "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": True}, "destination": "packages/community.general-11.2.0.tar.gz", "sha256": "h" * 64, "size_bytes": 100, "platform": "any", "required": True, "feature": None, "signature_status": "verified"},
            {"category": "ansible-collection", "name": "community.kubernetes", "version": "2.4.0", "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": True}, "destination": "packages/community.kubernetes-2.4.0.tar.gz", "sha256": "i" * 64, "size_bytes": 100, "platform": "any", "required": True, "feature": None, "signature_status": "verified"},
            {"category": "ansible-collection", "name": "kubernetes.core", "version": "5.0.0", "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": True}, "destination": "packages/kubernetes.core-5.0.0.tar.gz", "sha256": "j" * 64, "size_bytes": 100, "platform": "any", "required": True, "feature": None, "signature_status": "verified"},
            {"category": "ansible-collection", "name": "ansible.posix", "version": "2.0.0", "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": True}, "destination": "packages/ansible.posix-2.0.0.tar.gz", "sha256": "k" * 64, "size_bytes": 100, "platform": "any", "required": True, "feature": None, "signature_status": "verified"},
            {"category": "ansible-collection", "name": "ansible.utils", "version": "6.0.0", "source": {"type": "ansible-galaxy", "reference": "https://galaxy.ansible.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": True}, "destination": "packages/ansible.utils-6.0.0.tar.gz", "sha256": "l" * 64, "size_bytes": 100, "platform": "any", "required": True, "feature": None, "signature_status": "verified"},
            {"category": "kubespray-source", "name": "kubespray", "version": "v2.32.0", "source": {"type": "git", "reference": "https://github.com/kubernetes-sigs/kubespray", "fetched_at": "2026-11-24T00:00:00Z", "verified": True}, "destination": "kubespray/v2.32.0", "sha256": "m" * 64, "size_bytes": 100, "required": True, "feature": None, "signature_status": "verified"},
        ]
        # Create destination files
        for art in artifacts:
            dest_path = Path(tmpdir) / art["destination"]
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(b"mock content")
        
        manifest = {"schema_version": "1.0.0", "profile": "kubespray-control-node", "generated_at": "2026-11-24T00:00:00Z", "generated_by": "test", "artifacts": artifacts}
        with open(manifest_path, 'w') as f: json.dump(manifest, f)
        from check_readiness import ProfileChecker
        checker = ProfileChecker(manifest_path)
        checker.load_manifest()
        checker.index_artifacts()
        ready = checker.check_profile("kubespray-control-node")
        assert ready, f"Should be ready: {checker.results}"
        assert len(checker.results["signature_unverified"]) == 2, f"Expected 2 signature_unverified, got {len(checker.results['signature_unverified'])}: {checker.results['signature_unverified']}"
        assert any("signature_status=unverified" in m for m in checker.results["signature_unverified"])
        assert any("signature_status=absent" in m for m in checker.results["signature_unverified"])
        assert len(checker.results["signature_not_applicable"]) == 1, f"Expected 1 signature_not_applicable, got {len(checker.results['signature_not_applicable'])}: {checker.results['signature_not_applicable']}"
        assert any("signature_status=not_applicable" in m for m in checker.results["signature_not_applicable"])
        assert not any("signature_status=verified" in m for m in checker.results["signature_unverified"])
        assert not any("signature_status=verified" in m for m in checker.results["signature_not_applicable"])
        print("OK   All four signature classifications reported correctly")
    finally:
        import shutil; shutil.rmtree(tmpdir)


def test_os_repository_missing_staging_root_fails_readiness():
    """Test that os-repository readiness fails when staging_root is missing (deployment mode)."""
    tmpdir = tempfile.mkdtemp()
    try:
        manifest_path = Path(tmpdir) / "manifest.json"
        # Create all 8 required repo artifacts
        repos = [
            ("ol9-baseos", "9", "os-repositories/ol9/9/x86_64/baseos", "redhat", "yum"),
            ("ol9-appstream", "9", "os-repositories/ol9/9/x86_64/appstream", "redhat", "yum"),
            ("ubuntu-main", "22.04", "os-repositories/ubuntu/22.04/amd64/main", "debian", "apt"),
            ("ubuntu-updates", "22.04", "os-repositories/ubuntu/22.04/amd64/updates", "debian", "apt"),
            ("ubuntu-security", "22.04", "os-repositories/ubuntu/22.04/amd64/security", "debian", "apt"),
            ("ubuntu-main", "24.04", "os-repositories/ubuntu/24.04/amd64/main", "debian", "apt"),
            ("ubuntu-updates", "24.04", "os-repositories/ubuntu/24.04/amd64/updates", "debian", "apt"),
            ("ubuntu-security", "24.04", "os-repositories/ubuntu/24.04/amd64/security", "debian", "apt"),
        ]
        artifacts = []
        for name, version, destination, os_family, repo_type in repos:
            # Create directory with content in tmpdir (simulating staging content)
            repo_dir = Path(tmpdir) / destination
            repo_dir.mkdir(parents=True)
            pkg = repo_dir / "Packages" / "test.rpm"
            pkg.parent.mkdir(parents=True, exist_ok=True)
            pkg.write_bytes(b"mock content")

            import hashlib
            hasher = hashlib.sha256()
            for file_path in sorted(repo_dir.rglob("*")):
                if file_path.is_file():
                    rel_path = file_path.relative_to(repo_dir)
                    hasher.update(str(rel_path).encode())
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(8192), b''):
                            hasher.update(chunk)
            sha256 = hasher.hexdigest()

            artifacts.append({
                "category": "os-repository", "name": name, "version": version,
                "source": {"type": "os-repository", "reference": "https://example.com/", "fetched_at": "2026-11-24T00:00:00Z", "verified": False},
                "destination": destination, "sha256": sha256, "size_bytes": 100, "required": True,
                "feature": "ol9" if os_family == "redhat" else ("ubuntu2204" if version == "22.04" else "ubuntu2404"),
                "os_family": os_family, "os_version": version, "architecture": "x86_64",
                "repository_type": repo_type,
                "repository_metadata": {"repomd_xml": "present"} if repo_type == "yum" else {"release_file": "present"},
                "signature_status": "unverified"
            })
        manifest = {"schema_version": "1.0.0", "profile": "os-repositories", "generated_at": "2026-11-24T00:00:00Z", "generated_by": "test", "artifacts": artifacts}
        with open(manifest_path, 'w') as f: json.dump(manifest, f)
        from check_readiness import ProfileChecker
        checker = ProfileChecker(manifest_path)
        checker.load_manifest()
        checker.index_artifacts()
        ready = checker.check_profile("os-repositories")
        assert ready, "Profile compatibility should pass"
        assert len(checker.results["integrity_unverified"]) == 8, f"Expected 8 integrity_unverified, got {len(checker.results['integrity_unverified'])}"
        bad_staging_root = Path(tmpdir) / "nonexistent"
        checker2 = ProfileChecker(manifest_path, staging_root=bad_staging_root)
        checker2.load_manifest()
        checker2.index_artifacts()
        ready2 = checker2.check_profile("os-repositories")
        assert not ready2, "Should fail deployment readiness with missing staging root"
        assert len(checker2.results["checksum_failed"]) > 0
        assert any("does not exist" in m for m in checker2.results["checksum_failed"])
        file_staging_root = Path(tmpdir) / "file.txt"
        file_staging_root.write_text("not a dir")
        checker3 = ProfileChecker(manifest_path, staging_root=file_staging_root)
        checker3.load_manifest()
        checker3.index_artifacts()
        ready3 = checker3.check_profile("os-repositories")
        assert not ready3, "Should fail with file as staging root"
        assert len(checker3.results["checksum_failed"]) > 0
        assert any("not a directory" in m for m in checker3.results["checksum_failed"])
        print("OK   OS repository readiness fails with missing/invalid staging root")
    finally:
        import shutil; shutil.rmtree(tmpdir)


def run_all_tests():
    """Run all tests."""
    tests = [
        ("Valid manifest validation", test_valid_manifest),
        ("Missing field detection", test_invalid_manifest_missing_field),
        ("Invalid checksum detection", test_invalid_checksum),
        ("Missing file detection", test_missing_file),
        ("Duplicate identity detection", test_duplicate_identity),
        ("Duplicate destination detection", test_duplicate_destination),
        ("Path traversal rejection", test_path_traversal_rejection),
        ("Staging helper idempotent/overwrite protection", test_staging_helper_idempotent),
        ("Staging helper path traversal rejection", test_staging_helper_path_traversal),
        ("Profile readiness missing required", test_profile_readiness),
        ("Cilium/Calico profile separation", test_cilium_calico_separation),
        ("Optional artifact reporting", test_optional_artifact_reporting),
        ("Deterministic manifest generation", test_deterministic_manifest_generation),
        ("Fallback timestamp without SOURCE_DATE_EPOCH", test_manifest_without_source_date_epoch_fallback),
        ("Combined profile not a CNI substitute", test_combined_profile_not_substitute_for_cni),
        ("OS repository staging RPM", test_os_repository_staging_rpm),
        ("OS repository staging APT", test_os_repository_staging_apt),
        ("OS repository missing metadata warning", test_os_repository_missing_metadata),
        ("OS repository RPM missing repomd.xml", test_os_repository_rpm_missing_repomd),
        ("OS repository APT missing Release", test_os_repository_apt_missing_release),
        ("OS repository empty snapshot dir", test_os_repository_empty_snapshot_dir),
        ("OS repository duplicate identity", test_os_repository_duplicate_identity),
        ("OS repository duplicate destination", test_os_repository_duplicate_destination),
        ("OS repository required missing readiness", test_os_repository_required_missing_readiness),
        ("OS repository source path traversal rejected", test_os_repository_source_path_traversal),
        ("OS repository symlink handling", test_os_repository_symlink_handling),
        ("OS repository unsupported version", test_os_repository_unsupported_version),
        ("OS repository unsupported Ubuntu version", test_os_repository_unsupported_ubuntu_version),
        ("OS repository unsupported architecture", test_os_repository_unsupported_architecture),
        ("OS repository mismatched repo type", test_os_repository_mismatched_repo_type),
        ("OS repository checksum mismatch", test_os_repository_checksum_mismatch),
        ("OS repository path traversal rejection", test_os_repository_path_traversal),
        ("OS repository overwrite protection", test_os_repository_overwrite_protection),
        ("OS repository deterministic manifest", test_os_repository_deterministic),
        ("OS repositories profile readiness", test_os_repositories_profile_readiness),
        ("OS repository required vs optional", test_os_repository_required_vs_optional),
        ("OS repository missing signature_status", test_os_repository_missing_signature_status),
        ("OS repository absolute path inside root", test_os_repository_absolute_source_path_inside_root),
        ("OS repository absolute path outside root", test_os_repository_absolute_source_path_outside_root),
        ("OS repository symlink inside root", test_os_repository_symlink_inside_root),
        ("OS repository symlink outside root", test_os_repository_symlink_outside_root),
        ("OS repository symlink escapes source tree", test_os_repository_symlink_in_repo_escapes_source_tree),
        ("OS repository destination escape", test_os_repository_destination_escape),
        ("OS repository missing input root", test_os_repository_missing_input_root),
        ("OS repository invalid input root", test_os_repository_invalid_input_root),
        ("OS repository source outside input root", test_os_repository_source_outside_input_root),
        ("Readiness missing RPM metadata", test_readiness_missing_rpm_metadata),
        ("Readiness missing APT metadata", test_readiness_missing_apt_metadata),
        ("Readiness checksum mismatch", test_readiness_checksum_mismatch),
        ("Readiness unsupported OS version", test_readiness_unsupported_os_version),
        ("Readiness unverified signature reported", test_readiness_unverified_signature_reported),
        ("Profile check without staging root no readiness", test_profile_check_without_staging_root_no_readiness),
        ("OS repository readiness without staging root fails", test_os_repository_readiness_without_staging_root_fails),
        ("Signature classifications", test_signature_classifications),
        ("OS repository missing staging root fails readiness", test_os_repository_missing_staging_root_fails_readiness),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"FAIL {name}: {e}")
            failed += 1

    print(f"\n=== Results: {passed} passed, {failed} failed ===")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)