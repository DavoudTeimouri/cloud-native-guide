#!/usr/bin/env python3
"""Offline Profile Readiness Checker

Checks whether a staging directory contains all required artifacts for a selected profile.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional


# Profile requirements mapping
PROFILE_REQUIREMENTS = {
    "kubespray-control-node": {
        "python-package": [
            ("ansible", "12.3.0"),
            ("ansible-core", "2.19.3"),
            ("bcrypt", "<6"),
            ("cryptography", "50.0.1"),
            ("jmespath", "1.1.0"),
            ("netaddr", "1.3.0"),
            ("passlib", "1.7.4"),
        ],
        "ansible-collection": [
            ("community.general", "11.2.0"),
            ("community.kubernetes", "2.4.0"),
            ("kubernetes.core", "5.0.0"),
            ("ansible.posix", "2.0.0"),
            ("ansible.utils", "6.0.0"),
        ],
        "kubespray-source": [
            ("kubespray", "v2.32.0"),
        ],
    },
    "kubernetes-cilium": {
        "container-image": [
            ("kube-apiserver", "1.36.4"),
            ("kube-controller-manager", "1.36.4"),
            ("kube-scheduler", "1.36.4"),
            ("kube-proxy", "1.36.4"),
            ("etcd", "3.6.14"),
            ("coredns", "1.14.2"),
            ("pause", "3.10"),
            ("cilium", "1.20.2"),
            ("cilium-operator", "1.20.2"),
            ("hubble-relay", "1.20.2"),
            ("hubble-ui", "1.20.2"),
            ("metrics-server", "0.8.1"),
        ],
    },
    "kubernetes-calico": {
        "container-image": [
            ("kube-apiserver", "1.36.4"),
            ("kube-controller-manager", "1.36.4"),
            ("kube-scheduler", "1.36.4"),
            ("kube-proxy", "1.36.4"),
            ("etcd", "3.6.14"),
            ("coredns", "1.14.2"),
            ("pause", "3.10"),
            ("calico-node", "3.31.7"),
            ("calico-kube-controllers", "3.31.7"),
            ("calico-typha", "3.31.7"),
            ("metrics-server", "0.8.1"),
        ],
    },
    "combined": {
        "python-package": [
            ("ansible", "12.3.0"),
            ("ansible-core", "2.19.3"),
            ("bcrypt", "<6"),
            ("cryptography", "50.0.1"),
            ("jmespath", "1.1.0"),
            ("netaddr", "1.3.0"),
            ("passlib", "1.7.4"),
        ],
        "ansible-collection": [
            ("community.general", "11.2.0"),
            ("community.kubernetes", "2.4.0"),
            ("kubernetes.core", "5.0.0"),
            ("ansible.posix", "2.0.0"),
            ("ansible.utils", "6.0.0"),
        ],
        "kubespray-source": [
            ("kubespray", "v2.32.0"),
        ],
        "container-image": [
            ("kube-apiserver", "1.36.4"),
            ("kube-controller-manager", "1.36.4"),
            ("kube-scheduler", "1.36.4"),
            ("kube-proxy", "1.36.4"),
            ("etcd", "3.6.14"),
            ("coredns", "1.14.2"),
            ("pause", "3.10"),
            ("metrics-server", "0.8.1"),
        ],
    },
    "os-repositories": {
        "os-repository": [
            ({"name": "ol9-baseos", "version": "9", "os_version": "9"}),
            ({"name": "ol9-appstream", "version": "9", "os_version": "9"}),
            ({"name": "ubuntu-main", "version": "22.04", "os_version": "22.04"}),
            ({"name": "ubuntu-updates", "version": "22.04", "os_version": "22.04"}),
            ({"name": "ubuntu-security", "version": "22.04", "os_version": "22.04"}),
            ({"name": "ubuntu-main", "version": "24.04", "os_version": "24.04"}),
            ({"name": "ubuntu-updates", "version": "24.04", "os_version": "24.04"}),
            ({"name": "ubuntu-security", "version": "24.04", "os_version": "24.04"}),
        ],
    },
}


class ProfileChecker:
    def __init__(self, manifest_path, staging_root=None):
        self.manifest_path = manifest_path
        self.staging_root = staging_root or manifest_path.parent
        self._staging_root_explicit = staging_root is not None
        self.manifest = None
        self.artifacts_by_category = {}
        self.results = {
            "ready": [],
            "missing_required": [],
            "missing_optional": [],
            "checksum_failed": [],
            "unverified_source": [],
            "metadata_missing": [],
            "empty_snapshot": [],
            "signature_unverified": [],
            "signature_not_applicable": [],
            "integrity_unverified": [],
        }

    def load_manifest(self):
        try:
            with open(self.manifest_path, "r") as fp:
                self.manifest = json.load(fp)
            return True
        except (json.JSONDecodeError, OSError) as e:
            print("Error loading manifest: %s" % e, file=sys.stderr)
            return False

    def index_artifacts(self):
        self.artifacts_by_category = {}
        if not self.manifest:
            return
        for artifact in self.manifest.get("artifacts", []):
            cat = artifact.get("category", "other")
            if cat not in self.artifacts_by_category:
                self.artifacts_by_category[cat] = []
            self.artifacts_by_category[cat].append(artifact)

    def find_artifact(self, category, name, version, os_version=None):
        artifacts = self.artifacts_by_category.get(category, [])
        for artifact in artifacts:
            if artifact.get("name") == name and artifact.get("version") == version:
                if category == "os-repository" and os_version:
                    if artifact.get("os_version") != os_version:
                        continue
                return artifact, artifact.get("required", False)
        return None, False

    def check_profile(self, profile):
        self.results = {
            "ready": [],
            "missing_required": [],
            "missing_optional": [],
            "checksum_failed": [],
            "unverified_source": [],
            "metadata_missing": [],
            "empty_snapshot": [],
            "signature_unverified": [],
            "signature_not_applicable": [],
            "integrity_unverified": [],
        }
        if profile not in PROFILE_REQUIREMENTS:
            print("Error: Unknown profile '%s'" % profile, file=sys.stderr)
            return False

        requirements = PROFILE_REQUIREMENTS[profile]
        all_passed = True
        has_os_repositories = any(
            category == "os-repository" for category in requirements.keys()
        )

        is_deployment_readiness = has_os_repositories and self._staging_root_explicit
        is_profile_compatibility = not is_deployment_readiness

        if is_deployment_readiness:
            if not self.staging_root.exists():
                self.results["checksum_failed"].append("Staging root does not exist: %s" % self.staging_root)
                all_passed = False
            elif not self.staging_root.is_dir():
                self.results["checksum_failed"].append("Staging root is not a directory: %s" % self.staging_root)
                all_passed = False
            elif not os.access(self.staging_root, os.R_OK):
                self.results["checksum_failed"].append("Staging root is not readable: %s" % self.staging_root)
                all_passed = False

        for category, required_items in requirements.items():
            for req in required_items:
                if isinstance(req, dict):
                    name = req["name"]
                    version = req["version"]
                    os_version = req.get("os_version")
                    artifact, is_required = self.find_artifact(category, name, version, os_version)
                else:
                    name, version = req
                    artifact, is_required = self.find_artifact(category, name, version)
                
                is_required = True
                if artifact is None:
                    if is_required:
                        self.results["missing_required"].append("%s/%s@%s" % (category, name, version))
                        all_passed = False
                    else:
                        self.results["missing_optional"].append("%s/%s@%s" % (category, name, version))
                else:
                    sha256 = artifact.get("sha256", "")
                    if not sha256 or len(sha256) != 64:
                        self.results["checksum_failed"].append("%s/%s@%s (missing or invalid checksum)" % (category, name, version))
                        all_passed = False
                    if is_deployment_readiness:
                        dest = artifact.get("destination", "")
                        if dest:
                            file_path = self.staging_root / dest
                            if file_path.exists():
                                import hashlib
                                hasher = hashlib.sha256()
                                try:
                                    if file_path.is_file():
                                        with open(file_path, "rb") as fp:
                                            for chunk in iter(lambda: fp.read(8192), b""):
                                                hasher.update(chunk)
                                    elif file_path.is_dir():
                                        for sub_path in sorted(file_path.rglob("*")):
                                            if sub_path.is_file():
                                                rel_path = sub_path.relative_to(file_path)
                                                hasher.update(str(rel_path).encode())
                                                with open(sub_path, "rb") as fp:
                                                    for chunk in iter(lambda: fp.read(8192), b""):
                                                        hasher.update(chunk)
                                        actual_sha256 = hasher.hexdigest().lower()
                                        if actual_sha256 != sha256.lower():
                                            self.results["checksum_failed"].append("%s/%s@%s (checksum mismatch)" % (category, name, version))
                                            all_passed = False
                                except OSError as e:
                                    self.results["checksum_failed"].append("%s/%s@%s (cannot read: %s)" % (category, name, version, e))
                                    all_passed = False
                            else:
                                self.results["checksum_failed"].append("%s/%s@%s (file not found)" % (category, name, version))
                                all_passed = False
                        
                    if category == "os-repository" and is_deployment_readiness:
                        repo_meta = artifact.get("repository_metadata", {})
                        repo_type = artifact.get("repository_type", "")
                        if repo_type == "yum" and "repomd_xml" not in repo_meta:
                            self.results["metadata_missing"].append("%s/%s@%s (missing repomd_xml in repository_metadata)" % (category, name, version))
                            all_passed = False
                        elif repo_type == "apt" and "release_file" not in repo_meta:
                            self.results["metadata_missing"].append("%s/%s@%s (missing release_file in repository_metadata)" % (category, name, version))
                            all_passed = False
                    
                    dest = artifact.get("destination", "")
                    if dest and category == "os-repository":
                        file_path = self.staging_root / dest
                        if not file_path.exists() or not file_path.is_dir():
                            self.results["empty_snapshot"].append("%s/%s@%s (directory not found or not a directory)" % (category, name, version))
                            all_passed = False
                        else:
                            has_files = any(file_path.rglob("*"))
                            if not has_files:
                                self.results["empty_snapshot"].append("%s/%s@%s (empty snapshot directory)" % (category, name, version))
                                all_passed = False
                    
                    # Check integrity_unverified for os-repository in profile compatibility mode
                    if category == "os-repository" and is_profile_compatibility:
                        self.results["integrity_unverified"].append("%s/%s@%s (artifact integrity not verified: no staging root provided)" % (category, name, version))
                    
                    sig_status = artifact.get("signature_status", "")
                    if sig_status in ["unverified", "absent"]:
                        self.results["signature_unverified"].append("%s/%s@%s (signature_status=%s)" % (category, name, version, sig_status))
                    elif sig_status == "not_applicable":
                        self.results["signature_not_applicable"].append("%s/%s@%s (signature_status=not_applicable)" % (category, name, version))
                        
                        if all_passed:
                            self.results["ready"].append("%s/%s@%s" % (category, name, version))
                        source = artifact.get("source", {})
                        if not source.get("verified", False):
                            self.results["unverified_source"].append("%s/%s@%s (source not verified)" % (category, name, version))

        return all_passed

    def print_report(self, profile):
        print("\n=== Profile Readiness Report: %s ===" % profile)
        print("Manifest: %s" % self.manifest_path)
        print("Profile: %s" % (self.manifest.get("profile", "unknown") if self.manifest else "N/A"))

        total_required = sum(len(v) for v in PROFILE_REQUIREMENTS.get(profile, {}).values())
        total_ready = len(self.results["ready"])
        total_missing_required = len(self.results["missing_required"])
        total_missing_optional = len(self.results["missing_optional"])
        total_checksum_failed = len(self.results["checksum_failed"])
        total_unverified = len(self.results["unverified_source"])
        total_metadata_missing = len(self.results["metadata_missing"])
        total_empty_snapshot = len(self.results["empty_snapshot"])
        total_signature_unverified = len(self.results["signature_unverified"])
        total_signature_not_applicable = len(self.results["signature_not_applicable"])
        total_integrity_unverified = len(self.results["integrity_unverified"])

        print("\nSummary:")
        print("  Required artifacts: %d" % total_required)
        print("  Ready: %d" % total_ready)
        print("  Missing (required): %d" % total_missing_required)
        print("  Missing (optional): %d" % total_missing_optional)
        print("  Checksum issues: %d" % total_checksum_failed)
        print("  Unverified sources: %d" % total_unverified)
        print("  Missing metadata: %d" % total_metadata_missing)
        print("  Empty snapshots: %d" % total_empty_snapshot)
        print("  Unverified signatures: %d" % total_signature_unverified)
        print("  Signature not applicable: %d" % total_signature_not_applicable)
        print("  Integrity unverified: %d" % total_integrity_unverified)

        if self.results["ready"]:
            print("\nReady (%d):" % len(self.results["ready"]))
            for item in self.results["ready"]:
                print("  ✓ %s" % item)

        if self.results["missing_required"]:
            print("\nMissing Required (%d):" % len(self.results["missing_required"]))
            for item in self.results["missing_required"]:
                print("  ✗ %s" % item)

        if self.results["missing_optional"]:
            print("\nMissing Optional (%d):" % len(self.results["missing_optional"]))
            for item in self.results["missing_optional"]:
                print("  - %s" % item)

        if self.results["checksum_failed"]:
            print("\nChecksum Issues (%d):" % len(self.results["checksum_failed"]))
            for item in self.results["checksum_failed"]:
                print("  ! %s" % item)

        if self.results["unverified_source"]:
            print("\nUnverified Sources (%d):" % len(self.results["unverified_source"]))
            for item in self.results["unverified_source"]:
                print("  ? %s" % item)

        if self.results["metadata_missing"]:
            print("\nMissing Metadata (%d):" % len(self.results["metadata_missing"]))
            for item in self.results["metadata_missing"]:
                print("  ! %s" % item)

        if self.results["empty_snapshot"]:
            print("\nEmpty Snapshots (%d):" % len(self.results["empty_snapshot"]))
            for item in self.results["empty_snapshot"]:
                print("  ! %s" % item)

        if self.results["signature_unverified"]:
            print("\nUnverified Signatures (%d):" % len(self.results["signature_unverified"]))
            for item in self.results["signature_unverified"]:
                print("  ? %s" % item)

        if self.results["signature_not_applicable"]:
            print("\nSignature Not Applicable (%d):" % len(self.results["signature_not_applicable"]))
            for item in self.results["signature_not_applicable"]:
                print("  ~ %s" % item)

        if self.results["integrity_unverified"]:
            print("\nIntegrity Unverified (%d):" % len(self.results["integrity_unverified"]))
            for item in self.results["integrity_unverified"]:
                print("  ~ %s" % item)

        is_ready = (len(self.results["missing_required"]) == 0 and len(self.results["checksum_failed"]) == 0 
                    and len(self.results["metadata_missing"]) == 0 and len(self.results["empty_snapshot"]) == 0)
        print("\nStatus: %s" % ("READY" if is_ready else "NOT READY"))

        return is_ready

def main():
    parser = argparse.ArgumentParser(description="Check offline profile readiness")
    parser.add_argument("manifest", type=Path, help="Path to manifest JSON file")
    parser.add_argument("--staging-root", type=Path, help="Staging directory root (default: manifest parent)")
    parser.add_argument("--profile", required=True, choices=list(PROFILE_REQUIREMENTS.keys()), help="Profile to check")
    args = parser.parse_args()

    checker = ProfileChecker(args.manifest, args.staging_root)
    if not checker.load_manifest():
        return 1
    checker.index_artifacts()
    ready = checker.check_profile(args.profile)
    checker.print_report(args.profile)

    return 0 if ready else 1

if __name__ == "__main__":
    sys.exit(main())
