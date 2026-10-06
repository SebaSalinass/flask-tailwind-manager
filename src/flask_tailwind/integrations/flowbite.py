from .models import BrowserAsset, Integration, NpmRequirement, PackageEntry, PackagePath

FLOWBITE = Integration(
    name="flowbite",
    packages=(NpmRequirement("flowbite", "^3"),),
    sources=(PackagePath("flowbite", "**/*.js"),),
    plugins=(PackageEntry("flowbite", "plugin"),),
    assets=(
        BrowserAsset(
            "flowbite", "dist/flowbite.min.js", "vendor/flowbite/flowbite.min.js"
        ),
    ),
)
