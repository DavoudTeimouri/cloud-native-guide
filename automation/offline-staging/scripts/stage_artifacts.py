#!/usr/bin/env python3
"""Offline Staging Helper

Safely copies approved artifacts into a deterministic staging layout,
generates SHA-256 checksums, and produces a manifest.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

# Deterministic timestamp for reproducibility
# Can be overridden via SOURCE_DATE_EPOCH environment variable (reproducible builds standard)
DETERMINISTIC_TIMESTAMP = os.environ.get("SOURCE_DATE_EPOCH")
if DETERMINISTIC_TIMESTAMP:
    try:
        DETERMINISTIC_DT = datetime.fromtimestamp(int(DETERMINISTIC_TIMESTAMP), tz=timezone.utc)
    except (ValueError, OSError):
        DETERMINISTIC_DT = None
else:
    DETERMINISTIC_DT = None


def get_deterministic_timestamp() -> str:
    """Return deterministic ISO timestamp for reproducibility."""
    if DETERMINISTIC_DT:
        return DETERMINISTIC_DT.isoformat().replace("+00:00", "Z")
    # Fallback to a fixed timestamp if no SOURCE_DATE_EPOCH
    return "1970-01-01T00:00:00Z"


class StagingHelper:
    def __init__(self, staging_root: Path, manifest_path: Path, force: bool = False, input_root: Path = None):
        self.staging_root = staging_root.resolve()
        self.manifest_path = manifest_path.resolve()
        self.force = force
        if input_root:
            self.input_root = input_root.resolve()
            if not self.input_root.exists():
                raise ValueError(f"Input root does not exist: {self.input_root}")
            if not self.input_root.is_dir():
                raise ValueError(f"Input root is not a directory: {self.input_root}")
        else:
            self.input_root = None
        self.artifacts: List[Dict[str, Any]] = []
        self.existing_manifest: Optional[Dict] = None

    def load_existing_manifest(self) -> bool:
        """Load existing manifest if present."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, 'r') as f:
                    self.existing_manifest = json.load(f)
                return True
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Cannot load existing manifest: {e}", file=sys.stderr)
        return False

    def add_artifact(
        self,
        category: str,
        name: str,
        version: str,
        source_type: str,
        source_reference: str,
        source_path: Path,
        destination: str,
        required: bool = True,
        feature: Optional[str] = None,
        platform: Optional[str] = None,
        fetched_at: Optional[str] = None,
        verified: bool = False,
        os_family: Optional[str] = None,
        os_version: Optional[str] = None,
        architecture: Optional[str] = None,
        repository_type: Optional[str] = None,
        repository_metadata: Optional[Dict] = None,
        signature_status: Optional[str] = None
    ) -> bool:
        """Add an artifact to staging.

        Returns True on success, False on failure.
        """
        # Validate category
        valid_categories = ["python-package", "ansible-collection", "kubespray-source",
                           "container-image", "os-package", "ca-certificate", "other", "os-repository"]
        if category not in valid_categories:
            print(f"Error: Invalid category '{category}'", file=sys.stderr)
            return False

        # Validate source type
        valid_source_types = ["pypi", "ansible-galaxy", "git", "oci-registry",
                             "local-mirror", "internal-nexus", "internal-harbor", "other", "os-repository"]
        if source_type not in valid_source_types:
            print(f"Error: Invalid source_type '{source_type}'", file=sys.stderr)
            return False

        # Validate OS-specific fields
        if category in ["os-repository", "os-package"]:
            if not os_family:
                print(f"Error: os_family is required for category '{category}'", file=sys.stderr)
                return False
            if os_family not in ["redhat", "debian"]:
                print(f"Error: Invalid os_family '{os_family}' (must be redhat or debian)", file=sys.stderr)
                return False

            if not os_version:
                print(f"Error: os_version is required for category '{category}'", file=sys.stderr)
                return False

            if not architecture:
                print(f"Error: architecture is required for category '{category}'", file=sys.stderr)
                return False
            if architecture not in ["x86_64", "aarch64"]:
                print(f"Error: Invalid architecture '{architecture}' (must be x86_64 or aarch64)", file=sys.stderr)
                return False

            # Validate supported OS/version/architecture combinations
            if os_family == "redhat":
                if os_version != "9":
                    print(f"Error: Unsupported Oracle Linux version '{os_version}' (only 9 is supported)", file=sys.stderr)
                    return False
                if architecture != "x86_64":
                    print(f"Error: Unsupported architecture '{architecture}' for Oracle Linux (only x86_64 is supported)", file=sys.stderr)
                    return False
            elif os_family == "debian":
                if os_version not in ["22.04", "24.04"]:
                    print(f"Error: Unsupported Ubuntu version '{os_version}' (only 22.04, 24.04 are supported)", file=sys.stderr)
                    return False
                if architecture != "x86_64":
                    print(f"Error: Unsupported architecture '{architecture}' for Ubuntu (only x86_64 is supported)", file=sys.stderr)
                    return False

            if category == "os-repository":
                if not repository_type:
                    print(f"Error: repository_type is required for os-repository category", file=sys.stderr)
                    return False
                if repository_type not in ["yum", "apt"]:
                    print(f"Error: Invalid repository_type '{repository_type}' (must be yum or apt)", file=sys.stderr)
                    return False

                # Validate repository_type matches os_family
                if os_family == "redhat" and repository_type != "yum":
                    print(f"Error: Oracle Linux requires repository_type 'yum', got '{repository_type}'", file=sys.stderr)
                    return False
                if os_family == "debian" and repository_type != "apt":
                    print(f"Error: Ubuntu requires repository_type 'apt', got '{repository_type}'", file=sys.stderr)
                    return False

                if not signature_status:
                    print(f"Warning: signature_status is recommended for os-repository category", file=sys.stderr)
                elif signature_status not in ["verified", "unverified", "absent", "not_applicable"]:
                    print(f"Error: Invalid signature_status '{signature_status}'", file=sys.stderr)
                    return False

            # Mandatory input root for OS repository artifacts
            if category == "os-repository" and not self.input_root:
                print(f"Error: --input-root is required for os-repository artifacts", file=sys.stderr)
                return False

        # Resolve source path
        src = source_path.resolve()
        if not src.exists():
            print(f"Error: Source file or directory not found: {src}", file=sys.stderr)
            return False

        # Validate source path is within authorized input root (if configured)
        if self.input_root:
            try:
                src.relative_to(self.input_root)
            except ValueError:
                print(f"Error: Source path '{src}' escapes authorized input root '{self.input_root}'", file=sys.stderr)
                return False

        # Resolve destination path (relative to staging root)
        dest_path = self.staging_root / destination
        dest_path = dest_path.resolve()
        
        # Validate destination path doesn't escape staging root
        try:
            dest_path.relative_to(self.staging_root)
        except ValueError:
            print(f"Error: Destination path escapes staging root: {destination}", file=sys.stderr)
            return False

        # Safety: prevent path traversal
        try:
            dest_path.relative_to(self.staging_root)
        except ValueError:
            print(f"Error: Destination path escapes staging root: {destination}", file=sys.stderr)
            return False

        # Check if destination already exists
        if dest_path.exists() and not self.force:
            print(f"Error: Destination already exists (use --force to overwrite): {destination}", file=sys.stderr)
            return False

        # Ensure parent directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy file or directory
        try:
            if src.is_file():
                # Don't follow symlinks for files
                if src.is_symlink():
                    print(f"Error: Source is a symlink (not followed): {src}", file=sys.stderr)
                    return False
                shutil.copy2(src, dest_path)
            elif src.is_dir():
                # For directories, copy tree but don't follow symlinks that escape
                if dest_path.exists():
                    shutil.rmtree(dest_path)
                # Create destination directory
                dest_path.mkdir(parents=True, exist_ok=True)
                # Use copytree with custom ignore to skip symlinks that would escape
                def copy_without_escaping_symlinks(src_dir, dest_dir):
                    for item in src_dir.iterdir():
                        s = src_dir / item.name
                        d = dest_dir / item.name
                        if s.is_symlink():
                            # Check if symlink target escapes the source tree
                            target = s.resolve()
                            try:
                                target.relative_to(src)
                            except ValueError:
                                print(f"Error: Symlink '{s}' points outside source tree: {target}", file=sys.stderr)
                                return False
                            # Copy symlink as symlink
                            d.symlink_to(s.readlink())
                        elif s.is_file():
                            shutil.copy2(s, d)
                        elif s.is_dir():
                            d.mkdir(parents=True, exist_ok=True)
                            if not copy_without_escaping_symlinks(s, d):
                                return False
                    return True
                
                if not copy_without_escaping_symlinks(src, dest_path):
                    return False
            else:
                print(f"Error: Source is not a file or directory: {src}", file=sys.stderr)
                return False
        except OSError as e:
            print(f"Error copying: {e}", file=sys.stderr)
            return False

        # Compute SHA-256
        hasher = hashlib.sha256()
        try:
            if dest_path.is_file():
                with open(dest_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        hasher.update(chunk)
            else:
                # For directories, hash all files in deterministic order
                for file_path in sorted(dest_path.rglob("*")):
                    if file_path.is_file():
                        # Include relative path in hash for directory integrity
                        rel_path = file_path.relative_to(dest_path)
                        hasher.update(str(rel_path).encode())
                        with open(file_path, 'rb') as f:
                            for chunk in iter(lambda: f.read(8192), b''):
                                hasher.update(chunk)
            sha256 = hasher.hexdigest()
        except OSError as e:
            print(f"Error computing checksum: {e}", file=sys.stderr)
            return False

        # Get total size
        if dest_path.is_file():
            size = dest_path.stat().st_size
        else:
            size = sum(f.stat().st_size for f in dest_path.rglob("*") if f.is_file())

        # Create artifact entry with deterministic timestamps
        deterministic_fetched_at = fetched_at or get_deterministic_timestamp()
        artifact = {
            "category": category,
            "name": name,
            "version": version,
            "source": {
                "type": source_type,
                "reference": source_reference,
                "fetched_at": deterministic_fetched_at,
                "verified": verified
            },
            "destination": destination,
            "sha256": sha256,
            "size_bytes": size,
            "platform": platform,
            "required": required,
            "feature": feature
        }

        # Add OS-specific fields
        if category in ["os-repository", "os-package"]:
            artifact["os_family"] = os_family
            artifact["os_version"] = os_version
            artifact["architecture"] = architecture
        if category == "os-repository":
            artifact["repository_type"] = repository_type
            if repository_metadata is not None:
                artifact["repository_metadata"] = repository_metadata
            if signature_status:
                artifact["signature_status"] = signature_status

        self.artifacts.append(artifact)
        print(f"Staged: {destination} ({category}/{name}@{version}) sha256={sha256[:16]}...")
        return True

    def write_manifest(self, profile: str, generated_by: str = "offline-staging-helper") -> bool:
        """Write the manifest file with deterministic ordering."""
        if not self.artifacts:
            print("Error: No artifacts to write", file=sys.stderr)
            return False

        # Sort artifacts for deterministic ordering
        # Sort by category, then name, then version
        sorted_artifacts = sorted(self.artifacts, key=lambda a: (a["category"], a["name"], a["version"]))

        manifest = {
            "schema_version": "1.0.0",
            "profile": profile,
            "generated_at": get_deterministic_timestamp(),
            "generated_by": generated_by,
            "artifacts": sorted_artifacts
        }

        try:
            # Ensure parent directory exists
            self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2, sort_keys=True)
            print(f"Manifest written: {self.manifest_path}")
            return True
        except OSError as e:
            print(f"Error writing manifest: {e}", file=sys.stderr)
            return False

    def run(self, profile: str) -> bool:
        """Run the staging process (placeholder for custom implementations)."""
        return True


def main():
    parser = argparse.ArgumentParser(description="Offline Staging Helper")
    parser.add_argument("--staging-root", type=Path, required=True,
                        help="Staging directory root")
    parser.add_argument("--manifest", type=Path, required=True,
                        help="Manifest output path")
    parser.add_argument("--profile", required=True,
                        choices=["kubespray-control-node", "kubernetes-cilium",
                                "kubernetes-calico", "combined", "os-repositories"],
                        help="Artifact profile")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing files")
    parser.add_argument("--generated-by", default="offline-staging-helper",
                        help="Generator identifier for manifest")
    parser.add_argument("--input-root", type=Path,
                        help="Authorized input root directory (source paths must be within this)")

    # Artifact specification (repeatable)
    parser.add_argument("--artifact", action="append", default=[],
                        help="Artifact spec: category,name,version,source_type,source_ref,source_path,destination,required,feature,platform,os_family,os_version,architecture,repository_type,repository_metadata,signature_status")

    args = parser.parse_args()

    try:
        helper = StagingHelper(args.staging_root, args.manifest, args.force, args.input_root)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Load existing manifest to merge
    helper.load_existing_manifest()

    # Parse artifact specifications
    if not args.artifact:
        print("Error: At least one --artifact is required", file=sys.stderr)
        return 1

    for spec in args.artifact:
        parts = spec.split(",")
        if len(parts) < 7:
            print(f"Error: Invalid artifact spec (need 7+ fields): {spec}", file=sys.stderr)
            return 1

        category, name, version, source_type, source_ref, source_path, destination = parts[:7]
        required = parts[7].lower() == "true" if len(parts) > 7 else True
        feature = parts[8] if len(parts) > 8 else None
        platform = parts[9] if len(parts) > 9 else None
        os_family = parts[10] if len(parts) > 10 else None
        os_version = parts[11] if len(parts) > 11 else None
        architecture = parts[12] if len(parts) > 12 else None
        repository_type = parts[13] if len(parts) > 13 else None
        repository_metadata = json.loads(parts[14]) if len(parts) > 14 and parts[14] else None
        signature_status = parts[15] if len(parts) > 15 else None

        if not helper.add_artifact(
            category=category,
            name=name,
            version=version,
            source_type=source_type,
            source_reference=source_ref,
            source_path=Path(source_path),
            destination=destination,
            required=required,
            feature=feature,
            platform=platform,
            os_family=os_family,
            os_version=os_version,
            architecture=architecture,
            repository_type=repository_type,
            repository_metadata=repository_metadata,
            signature_status=signature_status
        ):
            return 1

    if not helper.write_manifest(args.profile, args.generated_by):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())