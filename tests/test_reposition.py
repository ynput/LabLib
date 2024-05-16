from lablib.operators import Transform, Crop
from fixtures import transform_op_data, crop_op_data


def test_Transform(transform_op_data):
    xfm = Transform.from_node_data(transform_op_data)
    oiio_args = xfm.to_oiio_args()

    # assert fields
    assert xfm.translate == [0.0, 0.0]
    assert xfm.rotate == 0.0
    assert xfm.scale == [0.0, 0.0]
    assert xfm.center == [0.0, 0.0]
    assert xfm.skewX == 0.0
    assert xfm.skewY == 0.0
    assert not xfm.invert

    # assert argument output
    assert oiio_args == [
        "--translate 0.0 0.0",
        "--rotate 0.0",
        "--scale 0.0 0.0",
        "--center 0.0 0.0",
    ]


def test_Crop(crop_op_data):
    crop = Crop.from_node_data(crop_op_data)
    oiio_args = crop.to_oiio_args()

    # assert fields
    assert crop.box == [0, 0, 1920, 1080]

    # assert argument output
    assert oiio_args == [
        "--crop 0,0,1920,1080",
    ]
