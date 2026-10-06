from .models import Integration, NpmRequirement, PackageEntry

DAISYUI = Integration(
    name="daisyui",
    packages=(NpmRequirement("daisyui", "^5"),),
    plugins=(PackageEntry("daisyui"),),
)
