import docker
from .generate_colormap import colormap
import shutil

def generateRelief(dataset, file_path, N=100):
    file_dir = 'C:\\Users\johan\Dropbox (MIT)\BASALT\pextant\pextant\maps\\'
    output_dir = 'C:\\Users\johan\Desktop\webapp\public\CustomMaps\\'

    regex_result = re.search('.+\/((\w+)\.tif)', file_path)
    file_name = regex_result.group(2)
    file_extension = regex_result.group(1)

    dataset = self.dataset
    clean_dataset = dataset[dataset > 0]
    altitude_lower_bound, altitude_upper_bound = np.min(clean_dataset), np.max(clean_dataset)

    # generate colormap.txt
    colormap(N, altitude_lower_bound, altitude_upper_bound)

    client = docker.from_env()
    container = "spara/gdal_ef"
    volume = {
        '/c/Users/johan/Dropbox (MIT)/BASALT/pextant/pextant/maps':
            {'bind': '/data',
             'mode': 'rw'},
    }

    # zoom into area this mesh covers
    zoom_name = "%s_zoomed.tif" % file_name
    zoom_command = 'gdal_translate %s %s -srcwin %s %s %s %s' \
                   % (file_extension, zoom_name, self.xoff, self.yoff, self.width, self.height)
    client.containers.run(container, zoom_command, volumes=volume)

    # generate relief image tif
    relief_name = "%s_relief_%s" % (file_name, N)
    relief_extension = "%s.tif" % relief_name
    colormap_command = "gdaldem color-relief %s colormap.txt %s -nearest_color_entry" \
                       % (zoom_name, relief_extension)
    client.containers.run(container, colormap_command, volumes=volume)

    # tile it!
    tile_command = "gdal2tiles.py %s" % relief_extension
    client.containers.run(container, tile_command, volumes=volume)

    from_dir = file_dir + relief_name
    to_dir = output_dir + relief_name
    shutil.move(from_dir,
                to_dir)