# blender-deusex-importer

Deus Ex t3d-files import plugin for [Blender](https://www.blender.org), that provides a simple method of importing level data (static geometry, positions of prefabs, light sources data) used in DeusEx game.

<img src="/images/unatco_island-1.png"/>

## Installation

1. Download io_import_deusex_t3d.py file from the root of this repository.
2. Open Blender 2.8 (or above) and Go to edit -> User Preferences...
3. In User Preferences select Add-ons on the left hand menu and then select the Install button on the top right side of the window.
4. Navigate to and select the downloaded file from step 1.
5. Select the check mark next to "Import-Export: DeusEx T3D Import" to activate the plugin.

## Usage

This tool will attempt to import DeusEx level data to the current blender scene.
The tool can be found in blender under File -> Import -> DeusEx T3D (*.t3d).
Selecting the add-on will open the file import window, where you can specify the location of the t3d file to import, as well as some options in the toolbar on the left.
Depending on what options are selected and the size and complexity of the Deus Ex level data, it may take time to import the t3d file.

## Add-on Options

Import Scale - the scaling factor that will be applied to the imported data.

Import Unvisuals - by selecting this option, the add-on will import prefabs positions and light sources data.

## Notes

The import functionality is currently limited to prefab positions, light sources and static geometry with no texture information.

<img src="/images/unatco_island-2.png"/>

<img src="/images/paris_everett-1.png"/>

<img src="/images/paris_everett-2.png"/>

<img src="/images/paris_everett-3.png"/>