import numpy as np

from Server.core.vision.system import VisionSystem


def test_multiple_vision_systems_independent_state():
    vs1 = VisionSystem()
    vs2 = VisionSystem({"stable": False})

    assert vs1.k["stable"] is True
    assert vs2.k["stable"] is False

    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    vs1.process_frame(frame)

    assert vs1.miss_count_big > 0
    assert vs2.miss_count_big == 0

    vs2.process_frame(frame)

    assert vs1.det_big is not vs2.det_big
