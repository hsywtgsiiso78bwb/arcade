"""
Functions and classes for managing a map created in the "Tiled Map Editor"
"""

from arcade import Sprite
from arcade import AnimatedTimeBasedSprite
from arcade import AnimationKeyframe
from arcade import SpriteList
import math
import pytiled_parser


def read_tmx(tmx_file: str) -> pytiled_parser.objects.TileMap:
    """
    Given a tmx_file, this will read in a tiled map, and return
    a TiledMap object.

    Given a tsx_file, the map will use it as the tileset.
    If tsx_file is not specified, it will use the tileset specified
    within the tmx_file.

    Important: Tiles must be a "collection" of images.

    Hitboxes can be drawn around tiles in the tileset editor,
    but only polygons are supported.
    (This is a great area for PR's to improve things.)

    :param str tmx_file: String with name of our TMX file

    :returns: Map
    :rtype: TiledMap
    """

    tile_map = pytiled_parser.parse_tile_map(tmx_file)
    if tile_map.background_color:
        color = pytiled_parser.utilities.parse_color(tile_map.background_color)
        tile_map.background_color = (color.red, color.green, color.blue)

    return tile_map


def get_tilemap_layer(map_object: pytiled_parser.objects.TileMap,
                      layer_name: str):

    assert isinstance(map_object, pytiled_parser.objects.TileMap)
    assert isinstance(layer_name, str)

    for layer in map_object.layers:
        if layer.name == layer_name:
            return layer

    return None


def _get_tile_by_gid(map_object: pytiled_parser.objects.TileMap, tile_gid: int) -> pytiled_parser.objects.Tile:
    # print()
    for tileset_key, tileset in map_object.tile_sets.items():
        for tile_key, tile in tileset.tiles.items():
            cur_tile_gid = tile.id_ + tileset_key
            # print(f"-- {cur_tile_gid} {tile.image.source}")
            if cur_tile_gid == tile_gid:
                tile.tileset = tileset
                return tile
    return None


def _get_tile_by_id(map_object: pytiled_parser.objects.TileMap, tileset: pytiled_parser.objects.TileSet, tile_id: int) -> pytiled_parser.objects.Tile:
    for tileset_key, cur_tileset in map_object.tile_sets.items():
        if cur_tileset is tileset:
            for tile_key, tile in cur_tileset.tiles.items():
                if tile_id == tile.id_:
                    return tile
    return None


def _create_sprite_from_tile(map_object, tile: pytiled_parser.objects.Tile,
                             scaling,
                             base_directory: str = ""):

    tmx_file = base_directory + tile.image.source

    # print(f"Creating tile: {tmx_file}")
    if tile.animation:
        # my_sprite = AnimatedTimeSprite(tmx_file, scaling)
        my_sprite = AnimatedTimeBasedSprite(tmx_file, scaling)
    else:
        my_sprite = Sprite(tmx_file, scaling)

    if tile.properties is not None and len(tile.properties) > 0:
        for property in tile.properties:
            my_sprite.properties[property.name] = property.value

        # print(tile.image.source, my_sprite.center_x, my_sprite.center_y)
    if tile.objectgroup is not None:
        if len(tile.objectgroup) > 1:
            print(f"Warning, only one hit box supported for tile with image {tile.image.source}.")

        for hitbox in tile.objectgroup:

            half_width = map_object.tile_size.width / 2
            half_height = map_object.tile_size.height / 2
            points = []
            if isinstance(hitbox, pytiled_parser.objects.RectangleObject):
                if hitbox.size is None:
                    print(
                        f"Warning: Rectangle hitbox created for without a height or width for {tile.image.source}. Ignoring.")
                    continue

                # print(tile.image.source, hitbox.location, hitbox.size)
                p1 = [hitbox.location[0] - half_width, half_height - hitbox.location[0]]
                p2 = [hitbox.location[0] + hitbox.size[0] - half_width, half_height - hitbox.size[0]]
                p3 = [hitbox.location[0] + hitbox.size[0] - half_width, half_height - (hitbox.location[1] + hitbox.size[1])]
                p4 = [hitbox.location[0] - half_width, half_height - (hitbox.location[1] + hitbox.size[1])]
                points = [p4, p3, p2, p1]

            elif isinstance(hitbox, pytiled_parser.objects.PolygonObject):
                for point in hitbox.points:
                    adj_x = point[0] + hitbox.location[0] - half_width
                    adj_y = half_height - (point[1] + hitbox.location[1])
                    adj_point = [adj_x, adj_y]
                    points.append(adj_point)

            elif isinstance(hitbox, pytiled_parser.objects.PolylineObject):
                for point in hitbox.points:
                    adj_x = point[0] + hitbox.x - half_width
                    adj_y = half_height - (point[1] + hitbox.y)
                    adj_point = [adj_x, adj_y]
                    points.append(adj_point)

                # See if we need to close the polyline
                if points[0][0] != points[-1][0] or points[0][1] != points[-1][1]:
                    points.append(points[0])

            elif isinstance(hitbox, pytiled_parser.objects.ElipseObject):
                if hitbox.size is None:
                    print(
                        f"Warning: Ellipse hitbox created for without a height or width for {tile.image.source}. Ignoring.")
                    continue
                w = hitbox.size[0] / 2
                h = hitbox.size[1] / 2
                cx = (hitbox.location[0] + hitbox.size[0] / 2) - half_width
                cy = map_object.tile_size.height - (hitbox.location[1] + hitbox.size[1] / 2) - half_height
                total_steps = 8
                angles = [step / total_steps * 2 * math.pi for step in range(total_steps)]
                for angle in angles:
                    x = w * math.cos(angle) + cx
                    y = h * math.sin(angle) + cy
                    point = [x, y]
                    points.append(point)

            else:
                print(f"Warning: Hitbox type {type(hitbox)} not supported.")

            # Scale the points to our sprite scaling
            for point in points:
                point[0] *= scaling
                point[1] *= scaling
            my_sprite.points = points

    if tile.animation is not None:
        key_frame_list = []
        for frame in tile.animation:
            frame_tile = _get_tile_by_id(map_object, tile.tileset, frame.tile_id)
            key_frame = AnimationKeyframe(frame.tile_id, frame.duration, frame_tile.image)
            key_frame_list.append(key_frame)

        my_sprite.frames = key_frame_list

    return my_sprite

def _process_object_layer(map_object: pytiled_parser.objects.TileMap,
                          layer: pytiled_parser.objects.TileLayer,
                          scaling: float = 1,
                          base_directory: str = "") -> SpriteList:
    sprite_list = SpriteList()

    for cur_object in layer.tiled_objects:
        tile = _get_tile_by_gid(map_object, cur_object.gid)
        my_sprite = _create_sprite_from_tile(map_object, tile, scaling=scaling,
                                             base_directory=base_directory)

        my_sprite.right = cur_object.location.x * scaling
        my_sprite.top = (map_object.map_size.height * map_object.tile_size[1] - cur_object.location.y) * scaling

        if cur_object.properties is not None and 'change_x' in cur_object.properties:
            my_sprite.change_x = float(cur_object.properties['change_x'])

        if cur_object.properties is not None and 'change_y' in cur_object.properties:
            my_sprite.change_y = float(cur_object.properties['change_y'])

        if cur_object.properties is not None and 'boundary_bottom' in cur_object.properties:
            my_sprite.boundary_bottom = float(cur_object.properties['boundary_bottom'])

        if cur_object.properties is not None and 'boundary_top' in cur_object.properties:
            my_sprite.boundary_top = float(cur_object.properties['boundary_top'])

        if cur_object.properties is not None and 'boundary_left' in cur_object.properties:
            my_sprite.boundary_left = float(cur_object.properties['boundary_left'])

        if cur_object.properties is not None and 'boundary_right' in cur_object.properties:
            my_sprite.boundary_right = float(cur_object.properties['boundary_right'])


        my_sprite.properties.update(cur_object.properties)
        # sprite.properties
        sprite_list.append(my_sprite)
    return sprite_list


def _process_tile_layer(map_object: pytiled_parser.objects.TileMap,
                        layer: pytiled_parser.objects.TileLayer,
                        scaling: float = 1,
                        base_directory: str = "") -> SpriteList:
    sprite_list = SpriteList()
    map_array = layer.data

    # Loop through the layer and add in the wall list
    for row_index, row in enumerate(map_array):
        for column_index, item in enumerate(row):
            # Check for empty square
            if item == 0:
                continue

            tile = _get_tile_by_gid(map_object, item)
            if tile is None:
                print(f"Warning, couldn't find tile for item {item} in layer '{layer.name}' in file '{map_object.tmx_file}'.")
                continue

            my_sprite = _create_sprite_from_tile(map_object, tile, scaling=scaling,
                                                 base_directory=base_directory)

            my_sprite.right = column_index * (map_object.tile_size[0] * scaling)
            my_sprite.top = (map_object.map_size.height - row_index - 1) * (map_object.tile_size[1] * scaling)

            sprite_list.append(my_sprite)

    return sprite_list


def process_layer(map_object: pytiled_parser.objects.TileMap,
                  layer_name: str,
                  scaling: float = 1,
                  base_directory: str = "") -> SpriteList:

    if len(base_directory) > 0 and not base_directory.endswith("/"):
        base_directory += "/"

    layer = get_tilemap_layer(map_object, layer_name)
    if layer is None:
        print(f"Warning, no layer named '{layer_name}'.")
        return SpriteList()

    if isinstance(layer, pytiled_parser.objects.TileLayer):
        return _process_tile_layer(map_object, layer, scaling, base_directory)

    elif isinstance(layer, pytiled_parser.objects.ObjectLayer):
        return _process_object_layer(map_object, layer, scaling, base_directory)