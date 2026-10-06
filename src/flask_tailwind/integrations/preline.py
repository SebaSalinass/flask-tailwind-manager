from .models import BrowserAsset, Integration, NpmRequirement, PackageEntry, PackagePath

PRELINE = Integration(
    name="preline",
    packages=(
        NpmRequirement("preline", "^3"),
        NpmRequirement("@tailwindcss/forms", "^0.5"),
    ),
    sources=(PackagePath("preline", "dist/*.js"),),
    imports=(PackagePath("preline", "variants.css"),),
    plugins=(PackageEntry("@tailwindcss/forms"),),
    assets=(BrowserAsset("preline", "dist/preline.js", "vendor/preline/preline.js"),),
)
