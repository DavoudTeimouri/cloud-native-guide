#!/usr/bin/env python3
"""Offline Staging Manifest Validator

Validates manifest against schema and verifies checksums.
Returns 0 on success, non-zero on failure.
"""

import argparse
import hashlib
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from datetime import datetime


class ManifestValidator:
    def __init__(self, manifest_path: Path, staging_root: Path = None):
        self.manifest_path = manifest_path
        self.staging_root = staging_root or manifest_path.parent
        self.manifest = None
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def load_manifest(self) -> bool:
        """Load and parse the manifest file."""
        try:
            with open(self.manifest_path, 'r') as f:
                self.manifest = json.load(f)
            return True
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON: {e}")
            return False
        except OSError as e:
            self.errors.append(f"Cannot read manifest: {e}")
            return False

    def validate_schema(self) -> bool:
        """Validate required fields and structure."""
        if not self.manifest:
            return False

        # Check required top-level fields
        required_fields = ["schema_version", "profile", "artifacts"]
        for field in required_fields:
            if field not in self.manifest:
                self.errors.append(f"Missing required field: {field}")
                return False

        # Validate schema version
        if self.manifest.get("schema_version") != "1.0.0":
            self.errors.append(f"Unsupported schema_version: {self.manifest.get('schema_version')}")
            return False

        # Validate profile
        valid_profiles = ["kubespray-control-node", "kubernetes-cilium", "kubernetes-calico", "combined", "os-repositories"]
        if self.manifest.get("profile") not in valid_profiles:
            self.errors.append(f"Invalid profile: {self.manifest.get('profile')}")
            return False

        # Validate artifacts array
        artifacts = self.manifest.get("artifacts", [])
        if not isinstance(artifacts, list):
            self.errors.append("'artifacts' must be a list")
            return False

        if len(artifacts) == 0:
            self.errors.append("At least one artifact is required")
            return False

        return True

    def validate_artifacts(self) -> bool:
        """Validate each artifact entry."""
        if not self.manifest:
            return False

        artifacts = self.manifest.get("artifacts", [])
        seen_identities: Set[Tuple[str, str, str]] = set()
        seen_destinations: Dict[str, int] = {}

        for idx, artifact in enumerate(artifacts):
            prefix = f"artifact[{idx}]"

            # Required fields
            required = ["category", "name", "version", "source", "destination", "sha256", "required"]
            for field in required:
                if field not in artifact:
                    self.errors.append(f"{prefix}: missing required field '{field}'")

            # Validate category
            valid_categories = ["python-package", "ansible-collection", "kubespray-source",
                              "container-image", "os-package", "ca-certificate", "other", "os-repository"]
            if artifact.get("category") not in valid_categories:
                self.errors.append(f"{prefix}: invalid category '{artifact.get('category')}'")

            # Validate source object
            source = artifact.get("source", {})
            if not isinstance(source, dict):
                self.errors.append(f"{prefix}: 'source' must be an object")
            else:
                if "type" not in source or "reference" not in source:
                    self.errors.append(f"{prefix}: source missing 'type' or 'reference'")
                valid_source_types = ["pypi", "ansible-galaxy", "git", "oci-registry",
                                     "local-mirror", "internal-nexus", "internal-harbor", "other", "os-repository"]
                if source.get("type") not in valid_source_types:
                    self.errors.append(f"{prefix}: invalid source type '{source.get('type')}'")

            # Validate SHA-256
            sha256 = artifact.get("sha256", "")
            if not isinstance(sha256, str) or not all(c in "0123456789abcdef" for c in sha256) or len(sha256) != 64:
                self.errors.append(f"{prefix}: invalid SHA-256 format")

            # Validate destination path safety
            dest = artifact.get("destination", "")
            if dest:
                if dest.startswith("/") or ".." in dest:
                    self.errors.append(f"{prefix}: unsafe destination path '{dest}' (absolute or traversal)")
                # Track duplicate destinations
                if dest in seen_destinations:
                    self.errors.append(f"{prefix}: duplicate destination path '{dest}' (also at artifact[{seen_destinations[dest]}])")
                else:
                    seen_destinations[dest] = idx

            # Check for duplicate identities (category + name + version)
            identity = (artifact.get("category", ""), artifact.get("name", ""), artifact.get("version", ""))
            if identity in seen_identities:
                self.errors.append(f"{prefix}: duplicate artifact identity {identity}")
            else:
                seen_identities.add(identity)

            # Validate required is boolean
            if not isinstance(artifact.get("required"), bool):
                self.errors.append(f"{prefix}: 'required' must be boolean")

            # Validate feature if present
            feature = artifact.get("feature")
            if feature is not None and not isinstance(feature, str):
                self.errors.append(f"{prefix}: 'feature' must be string")

            # OS-specific validations
            category = artifact.get("category", "")
            if category in ["os-repository", "os-package"]:
                if "os_family" not in artifact:
                    self.errors.append(f"{prefix}: 'os_family' is required for category '{category}'")
                elif artifact.get("os_family") not in ["redhat", "debian"]:
                    self.errors.append(f"{prefix}: invalid os_family '{artifact.get('os_family')}'")

                if "os_version" not in artifact:
                    self.errors.append(f"{prefix}: 'os_version' is required for category '{category}'")

                if "architecture" not in artifact:
                    self.errors.append(f"{prefix}: 'architecture' is required for category '{category}'")
                elif artifact.get("architecture") not in ["x86_64", "aarch64"]:
                    self.errors.append(f"{prefix}: invalid architecture '{artifact.get('architecture')}'")

                # Validate supported OS/version/architecture combinations
                os_family = artifact.get("os_family")
                os_version = artifact.get("os_version")
                architecture = artifact.get("architecture")
                if os_family == "redhat":
                    if os_version != "9":
                        self.errors.append(f"{prefix}: unsupported Oracle Linux version '{os_version}' (only 9 is supported)")
                    if architecture != "x86_64":
                        self.errors.append(f"{prefix}: unsupported architecture '{architecture}' for Oracle Linux (only x86_64 is supported)")
                elif os_family == "debian":
                    if os_version not in ["22.04", "24.04"]:
                        self.errors.append(f"{prefix}: unsupported Ubuntu version '{os_version}' (only 22.04, 24.04 are supported)")
                    if architecture != "x86_64":
                        self.errors.append(f"{prefix}: unsupported architecture '{architecture}' for Ubuntu (only x86_64 is supported)")

                if category == "os-repository":
                    if "repository_type" not in artifact:
                        self.errors.append(f"{prefix}: 'repository_type' is required for os-repository category")
                    elif artifact.get("repository_type") not in ["yum", "apt"]:
                        self.errors.append(f"{prefix}: invalid repository_type '{artifact.get('repository_type')}'")

                    # Validate repository_type matches os_family
                    repo_type = artifact.get("repository_type")
                    if os_family == "redhat" and repo_type != "yum":
                        self.errors.append(f"{prefix}: Oracle Linux requires repository_type 'yum', got '{repo_type}'")
                    if os_family == "debian" and repo_type != "apt":
                        self.errors.append(f"{prefix}: Ubuntu requires repository_type 'apt', got '{repo_type}'")

                    if "repository_metadata" not in artifact:
                        self.warnings.append(f"{prefix}: 'repository_metadata' is recommended for os-repository category")
                    else:
                        # Validate repository metadata based on repository type
                        repo_type = artifact.get("repository_type")
                        repo_meta = artifact.get("repository_metadata", {})
                        if repo_type == "yum":
                            if "repomd_xml" not in repo_meta:
                                self.errors.append(f"{prefix}: RPM repository missing 'repomd_xml' in repository_metadata")
                        elif repo_type == "apt":
                            if "release_file" not in repo_meta:
                                self.errors.append(f"{prefix}: APT repository missing 'release_file' in repository_metadata")

                    if "signature_status" not in artifact:
                        self.warnings.append(f"{prefix}: 'signature_status' is recommended for os-repository category")
                    elif artifact.get("signature_status") not in ["verified", "unverified", "absent", "not_applicable"]:
                        self.errors.append(f"{prefix}: invalid signature_status '{artifact.get('signature_status')}'")

        return len(self.errors) == 0

    def verify_checksums(self) -> bool:
        """Verify SHA-256 checksums against staged files."""
        if not self.manifest:
            return False

        artifacts = self.manifest.get("artifacts", [])
        for idx, artifact in enumerate(artifacts):
            prefix = f"artifact[{idx}]"
            dest = artifact.get("destination", "")
            expected_sha256 = artifact.get("sha256", "").lower()

            if not dest or not expected_sha256:
                continue

            file_path = self.staging_root / dest
            if not file_path.exists():
                self.errors.append(f"{prefix}: file not found at '{dest}'")
                continue

            # Compute SHA-256
            hasher = hashlib.sha256()
            try:
                if file_path.is_file():
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(8192), b''):
                            hasher.update(chunk)
                elif file_path.is_dir():
                    # For directories, hash all files in deterministic order
                    for sub_path in sorted(file_path.rglob("*")):
                        if sub_path.is_file():
                            # Include relative path in hash for directory integrity
                            rel_path = sub_path.relative_to(file_path)
                            hasher.update(str(rel_path).encode())
                            with open(sub_path, 'rb') as f:
                                for chunk in iter(lambda: f.read(8192), b''):
                                    hasher.update(chunk)
                else:
                    self.errors.append(f"{prefix}: destination is not a file or directory: '{dest}'")
                    continue
                actual_sha256 = hasher.hexdigest().lower()
            except OSError as e:
                self.errors.append(f"{prefix}: cannot read '{dest}': {e}")
                continue

            if actual_sha256 != expected_sha256:
                self.errors.append(
                    f"{prefix}: checksum mismatch for '{dest}'\n"
                    f"  expected: {expected_sha256}\n"
                    f"  actual:   {actual_sha256}"
                )

        return len(self.errors) == 0

    def validate(self) -> bool:
        """Run all validation steps."""
        if not self.load_manifest():
            return False
        if not self.validate_schema():
            return False
        if not self.validate_artifacts():
            return False
        if not self.verify_checksums():
            return False
        return True

    def print_report(self):
        """Print validation report."""
        if self.errors:
            print("VALIDATION FAILED:")
            for err in self.errors:
                print(f"  ERROR: {err}")
        else:
            print("VALIDATION PASSED")
            print(f"  Profile: {self.manifest.get('profile')}")
            print(f"  Artifacts: {len(self.manifest.get('artifacts', []))}")
            required_count = sum(1 for a in self.manifest.get('artifacts', []) if a.get('required'))
            optional_count = sum(1 for a in self.manifest.get('artifacts', []) if not a.get('required'))
            print(f"  Required: {required_count}, Optional: {optional_count}")

        if self.warnings:
            print("\nWARNINGS:")
            for warn in self.warnings:
                print(f"  WARN: {warn}")


def main():
    parser = argparse.ArgumentParser(description="Validate offline staging manifest")
    parser.add_argument("manifest", type=Path, help="Path to manifest JSON file")
    parser.add_argument("--staging-root", type=Path, help="Staging directory root (default: manifest parent)")
    args = parser.parse_args()

    validator = ManifestValidator(args.manifest, args.staging_root)
    success = validator.validate()
    validator.print_report()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())