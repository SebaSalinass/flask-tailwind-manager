"""Value objects for Tailwind integration declarations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NpmRequirement:
    name: str
    version: str
    dev: bool = False


@dataclass(frozen=True)
class PackagePath:
    package: str
    path: str


@dataclass(frozen=True)
class PackageEntry:
    package: str
    subpath: str | None = None


@dataclass(frozen=True)
class BrowserAsset:
    package: str
    source: str
    destination: str


@dataclass(frozen=True)
class Integration:
    name: str
    packages: tuple[NpmRequirement, ...] = ()
    sources: tuple[PackagePath, ...] = ()
    imports: tuple[PackagePath, ...] = ()
    plugins: tuple[PackageEntry, ...] = ()
    assets: tuple[BrowserAsset, ...] = ()
