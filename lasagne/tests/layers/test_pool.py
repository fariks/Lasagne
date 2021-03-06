from mock import Mock
import numpy as np
import pytest
import theano

from lasagne.utils import floatX


def max_pool_1d(data, pool_size, stride=None):
    stride = pool_size if stride is None else stride

    idx = range(data.shape[-1])
    used_idx = set([])
    idx_sets = []

    i = 0
    while i < data.shape[-1]:
        idx_set = set(range(i, i + pool_size))
        idx_set = idx_set.intersection(idx)
        if not idx_set.issubset(used_idx):
            idx_sets.append(list(idx_set))
            used_idx = used_idx.union(idx_set)
        i += stride

    data_pooled = np.array(
        [data[..., idx_set].max(axis=-1) for idx_set in idx_sets])
    data_pooled = np.rollaxis(data_pooled, 0, len(data_pooled.shape))

    return data_pooled


def max_pool_1d_ignoreborder(data, pool_size, stride=None, pad=0):
    stride = pool_size if stride is None else stride

    pads = [(0, 0), ] * len(data.shape)
    pads[-1] = (pad, pad)
    data = np.pad(data, pads, mode='constant', constant_values=(-np.inf,))

    data_shifted = np.zeros((pool_size,) + data.shape)
    data_shifted = data_shifted[..., :data.shape[-1] - pool_size + 1]
    for i in range(pool_size):
        data_shifted[i] = data[..., i:i + data.shape[-1] - pool_size + 1]
    data_pooled = data_shifted.max(axis=0)

    if stride:
        data_pooled = data_pooled[..., ::stride]

    return data_pooled


def max_pool_2d(data, pool_size, stride):
    data_pooled = max_pool_1d(data, pool_size[1], stride[1])

    data_pooled = np.swapaxes(data_pooled, -1, -2)
    data_pooled = max_pool_1d(data_pooled, pool_size[0], stride[0])
    data_pooled = np.swapaxes(data_pooled, -1, -2)

    return data_pooled


def max_pool_2d_ignoreborder(data, pool_size, stride, pad):
    data_pooled = max_pool_1d_ignoreborder(
        data, pool_size[1], stride[1], pad[1])

    data_pooled = np.swapaxes(data_pooled, -1, -2)
    data_pooled = max_pool_1d_ignoreborder(
        data_pooled, pool_size[0], stride[0], pad[0])
    data_pooled = np.swapaxes(data_pooled, -1, -2)

    return data_pooled


class TestMaxPool1DLayer:
    def pool_test_sets():
        for pool_size in [2, 3]:
            for stride in [1, 2, 3, 4]:
                yield (pool_size, stride)

    def pool_test_sets_ignoreborder():
        for pool_size in [2, 3]:
            for stride in [1, 2, 3, 4]:
                for pad in range(pool_size):
                    yield (pool_size, stride, pad)

    def input_layer(self, output_shape):
        return Mock(get_output_shape=lambda: output_shape)

    def layer(self, input_layer, pool_size, stride=None, pad=0):
        from lasagne.layers.pool import MaxPool1DLayer
        return MaxPool1DLayer(
            input_layer,
            pool_size=pool_size,
            stride=stride,
            ignore_border=False,
        )

    def layer_ignoreborder(self, input_layer, pool_size, stride=None, pad=0):
        from lasagne.layers.pool import MaxPool1DLayer
        return MaxPool1DLayer(
            input_layer,
            pool_size=pool_size,
            stride=stride,
            pad=pad,
            ignore_border=True,
        )

    @pytest.mark.parametrize(
        "pool_size, stride", list(pool_test_sets()))
    def test_get_output_for(self, pool_size, stride):
        input = floatX(np.random.randn(8, 16, 23))
        input_layer = self.input_layer(input.shape)
        input_theano = theano.shared(input)
        layer_output = self.layer(
            input_layer, pool_size, stride).get_output_for(input_theano)

        layer_result = layer_output.eval()
        numpy_result = max_pool_1d(input, pool_size, stride)

        assert np.all(numpy_result.shape == layer_result.shape)
        assert np.allclose(numpy_result, layer_result)

    @pytest.mark.parametrize(
        "pool_size, stride, pad", list(pool_test_sets_ignoreborder()))
    def test_get_output_for_ignoreborder(self, pool_size, stride, pad):
        input = floatX(np.random.randn(8, 16, 23))
        input_layer = self.input_layer(input.shape)
        input_theano = theano.shared(input)
        layer_output = self.layer_ignoreborder(
            input_layer, pool_size, stride, pad).get_output_for(input_theano)

        layer_result = layer_output.eval()
        numpy_result = max_pool_1d_ignoreborder(input, pool_size, stride, pad)

        assert np.all(numpy_result.shape == layer_result.shape)
        assert np.allclose(numpy_result, layer_result)

    @pytest.mark.parametrize(
        "input_shape", [(32, 64, 128), (None, 64, 128), (32, None, 128)])
    def test_get_output_shape_for(self, input_shape):
        input_layer = self.input_layer(input_shape)
        layer = self.layer_ignoreborder(input_layer, pool_size=2)
        assert layer.get_output_shape_for((None, 64, 128)) == (None, 64, 64)
        assert layer.get_output_shape_for((32, 64, 128)) == (32, 64, 64)


class TestMaxPool2DLayer:
    def pool_test_sets():
        for pool_size in [2, 3]:
            for stride in [1, 2, 3, 4]:
                yield (pool_size, stride)

    def pool_test_sets_ignoreborder():
        for pool_size in [2, 3]:
            for stride in [1, 2, 3, 4]:
                for pad in range(pool_size):
                    yield (pool_size, stride, pad)

    def input_layer(self, output_shape):
        return Mock(get_output_shape=lambda: output_shape)

    def layer(self, input_layer, pool_size, stride=None,
              pad=(0, 0), ignore_border=False):
        from lasagne.layers.pool import MaxPool2DLayer
        return MaxPool2DLayer(
            input_layer,
            pool_size=pool_size,
            stride=stride,
            pad=pad,
            ignore_border=ignore_border,
        )

    @pytest.mark.parametrize(
        "pool_size, stride", list(pool_test_sets()))
    def test_get_output_for(self, pool_size, stride):
        try:
            input = floatX(np.random.randn(8, 16, 17, 13))
            input_layer = self.input_layer(input.shape)
            input_theano = theano.shared(input)
            result = self.layer(
                input_layer,
                (pool_size, pool_size),
                (stride, stride),
                ignore_border=False,
            ).get_output_for(input_theano)

            result_eval = result.eval()
            numpy_result = max_pool_2d(
                input, (pool_size, pool_size), (stride, stride))

            assert np.all(numpy_result.shape == result_eval.shape)
            assert np.allclose(result_eval, numpy_result)
        except NotImplementedError:
            pytest.skip()

    @pytest.mark.parametrize(
        "pool_size, stride, pad", list(pool_test_sets_ignoreborder()))
    def test_get_output_for_ignoreborder(self, pool_size,
                                         stride, pad):
        try:
            input = floatX(np.random.randn(8, 16, 17, 13))
            input_layer = self.input_layer(input.shape)
            input_theano = theano.shared(input)

            result = self.layer(
                input_layer,
                pool_size,
                stride,
                pad,
                ignore_border=True,
            ).get_output_for(input_theano)

            result_eval = result.eval()
            numpy_result = max_pool_2d_ignoreborder(
                input, (pool_size, pool_size), (stride, stride), (pad, pad))

            assert np.all(numpy_result.shape == result_eval.shape)
            assert np.allclose(result_eval, numpy_result)
        except NotImplementedError:
            pytest.skip()

    @pytest.mark.parametrize(
        "input_shape",
        [(32, 64, 24, 24), (None, 64, 24, 24), (32, None, 24, 24)],
    )
    def test_get_output_shape_for(self, input_shape):
        try:
            input_layer = self.input_layer(input_shape)
            layer = self.layer(input_layer,
                               pool_size=(2, 2), stride=None)
            assert layer.get_output_shape_for(
                (None, 64, 24, 24)) == (None, 64, 12, 12)
            assert layer.get_output_shape_for(
                (32, 64, 24, 24)) == (32, 64, 12, 12)
        except NotImplementedError:
            pytest.skip()


class TestMaxPool2DCCLayer:
    def pool_test_sets():
        for pool_size in [2, 3]:
            for stride in range(1, pool_size+1):
                yield (pool_size, stride)

    def input_layer(self, output_shape):
        return Mock(get_output_shape=lambda: output_shape)

    def layer(self, input_layer, pool_size, stride):
        try:
            from lasagne.layers.cuda_convnet import MaxPool2DCCLayer
        except ImportError:
            pytest.skip("cuda_convnet not available")
        return MaxPool2DCCLayer(
            input_layer,
            pool_size=pool_size,
            stride=stride,
        )

    @pytest.mark.parametrize(
        "pool_size, stride", list(pool_test_sets()))
    def test_get_output_for(self, pool_size, stride):
        try:
            input = floatX(np.random.randn(8, 16, 16, 16))
            input_layer = self.input_layer(input.shape)
            input_theano = theano.shared(input)
            result = self.layer(
                input_layer,
                (pool_size, pool_size),
                (stride, stride),
            ).get_output_for(input_theano)

            result_eval = result.eval()
            numpy_result = max_pool_2d(
                input, (pool_size, pool_size), (stride, stride))

            assert np.all(numpy_result.shape == result_eval.shape)
            assert np.allclose(result_eval, numpy_result)
        except NotImplementedError:
            pytest.skip()

    @pytest.mark.parametrize(
        "input_shape",
        [(32, 64, 24, 24), (None, 64, 24, 24), (32, None, 24, 24)],
    )
    def test_get_output_shape_for(self, input_shape):
        try:
            input_layer = self.input_layer(input_shape)
            layer = self.layer(input_layer,
                               pool_size=(2, 2), stride=None)
            assert layer.get_output_shape_for(
                (None, 64, 24, 24)) == (None, 64, 12, 12)
            assert layer.get_output_shape_for(
                (32, 64, 24, 24)) == (32, 64, 12, 12)
        except NotImplementedError:
            pytest.skip()


class TestMaxPool2DNNLayer:
    def pool_test_sets_ignoreborder():
        for pool_size in [2, 3]:
            for stride in [1, 2, 3, 4]:
                for pad in range(pool_size):
                    yield (pool_size, stride, pad)

    def input_layer(self, output_shape):
        return Mock(get_output_shape=lambda: output_shape)

    def layer(self, input_layer, pool_size, stride, pad):
        try:
            from lasagne.layers.dnn import MaxPool2DDNNLayer
        except ImportError:
            pytest.skip("cuDNN not available")

        return MaxPool2DDNNLayer(
            input_layer,
            pool_size=pool_size,
            stride=stride,
            pad=pad,
        )

    @pytest.mark.parametrize(
        "pool_size, stride, pad", list(pool_test_sets_ignoreborder()))
    def test_get_output_for_ignoreborder(self, pool_size,
                                         stride, pad):
        try:
            input = floatX(np.random.randn(8, 16, 17, 13))
            input_layer = self.input_layer(input.shape)
            input_theano = theano.shared(input)

            result = self.layer(
                input_layer,
                pool_size,
                stride,
                pad,
            ).get_output_for(input_theano)

            result_eval = result.eval()
            numpy_result = max_pool_2d_ignoreborder(
                input, (pool_size, pool_size), (stride, stride), (pad, pad))

            assert np.all(numpy_result.shape == result_eval.shape)
            assert np.allclose(result_eval, numpy_result)
        except NotImplementedError:
            pytest.skip()

    @pytest.mark.parametrize(
        "input_shape",
        [(32, 64, 24, 24), (None, 64, 24, 24), (32, None, 24, 24)],
    )
    def test_get_output_shape_for(self, input_shape):
        try:
            input_layer = self.input_layer(input_shape)
            layer = self.layer(input_layer,
                               pool_size=(2, 2), stride=None, pad=(0, 0))
            assert layer.get_output_shape_for(
                (None, 64, 24, 24)) == (None, 64, 12, 12)
            assert layer.get_output_shape_for(
                (32, 64, 24, 24)) == (32, 64, 12, 12)
        except NotImplementedError:
            raise
        #    pytest.skip()
