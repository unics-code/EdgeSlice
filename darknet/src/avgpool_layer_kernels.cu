#include "cuda_runtime.h"
#include "curand.h"
#include "cublas_v2.h"

extern "C" {
#include "avgpool_layer.h"
#include "cuda.h"
}

__global__ void forward_avgpool_layer_kernel(int n, int w, int h, int c,
		float *input, float *output, int ix, int iy, int iz) {
	int bx = blockIdx.x + ix;
	int by = blockIdx.y + iy;
	int bz = blockIdx.z + iz;

	int id = (bx + by * gridDim.x) * blockDim.x + threadIdx.x;
	if (id >= n)
		return;

	int k = id % c;
	id /= c;
	int b = id;

	int i;
	int out_index = (k + c * b);
	output[out_index] = 0;
	for (i = 0; i < w * h; ++i) {
		int in_index = i + h * w * (k + b * c);
		output[out_index] += input[in_index];
	}
	output[out_index] /= w * h;
}

__global__ void backward_avgpool_layer_kernel(int n, int w, int h, int c,
		float *in_delta, float *out_delta, int ix, int iy, int iz) {
	int bx = blockIdx.x + ix;
	int by = blockIdx.y + iy;
	int bz = blockIdx.z + iz;

	int id = (bx + by * gridDim.x) * blockDim.x + threadIdx.x;
	if (id >= n)
		return;

	int k = id % c;
	id /= c;
	int b = id;

	int i;
	int out_index = (k + c * b);
	for (i = 0; i < w * h; ++i) {
		int in_index = i + h * w * (k + b * c);
		in_delta[in_index] += out_delta[out_index] / (w * h);
	}
}

extern "C" void forward_avgpool_layer_gpu(avgpool_layer layer, network net) {
	size_t n = layer.c * layer.batch;

	if (VIRTUALGPU) {
		dim3 total_blocks = cuda_gridsize(n); int quato=QUATO;

		for (int iz = 0; iz < total_blocks.z; iz++) {
			for (int iy = 0; iy < total_blocks.y; iy++) {
				int ix = 0;

				for (ix = 0; ix < int(total_blocks.x / quato); ix++)
					forward_avgpool_layer_kernel<<<quato, BLOCK>>>(n, layer.w,
							layer.h, layer.c, net.input_gpu, layer.output_gpu,
							ix * quato, iy, iz);

				// if the iteration is not integer, run last time with fixed number blocks
				if (double(total_blocks.x)
						- quato * int(double(total_blocks.x) / quato) > 0)
					forward_avgpool_layer_kernel<<<total_blocks.x - quato * ix,
							BLOCK>>>(n, layer.w, layer.h, layer.c,
							net.input_gpu, layer.output_gpu, ix * quato, iy,
							iz);
			}
		}
	} else {
		forward_avgpool_layer_kernel<<<cuda_gridsize(n), BLOCK>>>(n, layer.w,
				layer.h, layer.c, net.input_gpu, layer.output_gpu, 0, 0, 0);
	}

	//forward_avgpool_layer_kernel<<<cuda_gridsize(n), BLOCK>>>(n, layer.w, layer.h, layer.c, net.input_gpu, layer.output_gpu);
	check_error(cudaPeekAtLastError());
}

extern "C" void backward_avgpool_layer_gpu(avgpool_layer layer, network net) {
	size_t n = layer.c * layer.batch;

	if (VIRTUALGPU) {
		dim3 total_blocks = cuda_gridsize(n); int quato=QUATO;

		for (int iz = 0; iz < total_blocks.z; iz++) {
			for (int iy = 0; iy < total_blocks.y; iy++) {
				int ix = 0;

				for (ix = 0; ix < int(total_blocks.x / quato); ix++)
					backward_avgpool_layer_kernel<<<quato, BLOCK>>>(n, layer.w,
							layer.h, layer.c, net.delta_gpu, layer.delta_gpu,
							ix * quato, iy, iz);

				// if the iteration is not integer, run last time with fixed number blocks
				if (double(total_blocks.x)
						- quato * int(double(total_blocks.x) / quato) > 0)
					backward_avgpool_layer_kernel<<<total_blocks.x - quato * ix,
							BLOCK>>>(n, layer.w, layer.h, layer.c,
							net.delta_gpu, layer.delta_gpu, ix * quato, iy, iz);
			}
		}
	} else {
		backward_avgpool_layer_kernel<<<cuda_gridsize(n), BLOCK>>>(n, layer.w,
				layer.h, layer.c, net.delta_gpu, layer.delta_gpu, 0, 0, 0);
	}

	// backward_avgpool_layer_kernel<<<cuda_gridsize(n), BLOCK>>>(n, layer.w, layer.h, layer.c, net.delta_gpu, layer.delta_gpu);
	check_error(cudaPeekAtLastError());
}

