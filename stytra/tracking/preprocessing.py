"""
    Preprocessing functions, take the current image, some state (optional,
    used for backgorund subtraction) and parameters and return the processed image

"""
import cv2

from stytra.tracking import ParametrizedImageproc
import numpy as np


class PreprocMethod(ParametrizedImageproc):
    def __init__(self):
        super().__init__()
        self.add_params(display_processed=False)


class Prefilter(PreprocMethod):
    def __init__(self):
        super().__init__()
        self.add_params(
            filter_size=0,
            image_scale=dict(type="float", value=0.5, limits=(0.01, 1.0)),
            color_invert=False,
        )

    # We have to rely on class methods here, as Parametrized objects can only
    # live in the main process
    @classmethod
    def process(
        cls,
        im,
        state=None,
        image_scale=1,
        filter_size=0,
        color_invert=False,
        **extraparams
    ):
        """ Optionally resizes, smooths and inverts the image

        :param im:
        :param state:
        :param filter_size:
        :param image_scale:
        :param color_invert:
        :return:
        """
        if image_scale != 1:
            im = cv2.resize(
                im, None, fx=image_scale, fy=image_scale, interpolation=cv2.INTER_AREA
            )
        if filter_size > 0:
            im = cv2.boxFilter(im, -1, (filter_size, filter_size))
        if color_invert:
            im = 255 - im

        return im, None


class BgSubState:
    """  A class which implements simple backgorund sutraction by keeping a
    the background model in a circular buffer

    """

    def __init__(self):
        self.collected_images = None
        self.i = 0

    def update(self, im, i_learn_every=1, learning_rate=0.01):
        if self.collected_images is None:
            self.collected_images = np.empty_like(im)
        elif self.i == 0:
            self.collected_images[:, :] = (im*learning_rate +\
                                           self.collected_images*(1-learning_rate)).astype(np.uint8)
        self.i = (self.i + 1) % i_learn_every

    def subtract(self, im):
        return cv2.absdiff(im, self.collected_images)

    def reset(self):
        self.n_collected = 0


class BackgorundSubtractor(PreprocMethod):
    def __init__(self):
        super().__init__()
        self.add_params(image_scale=dict(type="float", value=1,
                                         limits=(0.01, 1.0)),
            learning_rate=dict(type="float", value=0.01,
                           limits=(0.001, 1.0),
                           ),
            learn_every=dict(type="int", value=1, limits=(1, 1000))
        )
        self.collected_images = None

    @classmethod
    def process(cls, im, state=None, learning_rate=0.001,
                learn_every=1, image_scale=1, **extraparams):
        if image_scale != 1:
            im = cv2.resize(
                im, None, fx=image_scale, fy=image_scale, interpolation=cv2.INTER_AREA
            )
        if state is None:
            state = BgSubState()
        state.update(im, learn_every, learning_rate)
        return state.subtract(im), state


class CVSubtractorState:
    def __init__(self, method, threshold):
        self.method = method
        self.threshold = threshold
        if method == "knn":
            self.subtractor = cv2.createBackgroundSubtractorKNN(
                dist2Threshhold=threshold, detectShadows=False
            )
        else:
            self.subtractor = cv2.createBackgroundSubtractorMOG2(
                varThreshold=threshold, detectShadows=False
            )

    def update(self, im):
        return self.subtractor.apply(im)


class CV2BgSub(PreprocMethod):
    def __init__(self):
        super().__init__()
        self.add_params(
            method=dict(type="list", value="mog2", values=["knn", "mog2"]),
            threshold=128,
        )
        self.collected_images = None

    @classmethod
    def process(
        cls, im, state=None, method="mog2", image_scale=1, threshold=128, **extraparams
    ):
        if state is None or state.method != method or state.threshold != threshold:
            state = CVSubtractorState(method, threshold)
        return state.update(im), state
