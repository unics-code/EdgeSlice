#include "cuda_runtime.h"
#include "curand.h"
#include "cublas_v2.h"

extern "C" {
#include "dropout_layer.h"
#include "cuda.h"
#include "utils.h"
}

__global__ void yoloswag420blazeit360noscope(float *input, int size, float *rand, float prob, float scale, int ix, int iy, int iz)
{
	int bx = blockIdx.x + ix;
	int by = blockIdx.y + iy;
	int bz = blockIdx.z + iz;

    int id = (bx + by*gridDim.x) * blockDim.x + threadIdx.x;
    if(id < size) input[id] = (rand[id] < prob) ? 0 : input[id]*scale;
}

void forward_dropout_layer_gpu(dropout_layer layer, network net)
{
    if (!net.train) return;
    int size = layer.inputs*layer.batch;
    cuda_random(layer.rand_gpu, size);
    /*
    int i;
    for(i = 0; i < size; ++i){
        layer.rand[i] = rand_uniform();
    }
    cuda_push_array(layer.rand_gpu, layer.rand, size);
    */

	if (VIRTUALGPU)
	{
		dim3 total_blocks = cuda_gridsize(size); int quato=QUATO;

		for (int iz=0;iz<total_blocks.z;iz++)
		{
			for (int iy=0;iy<total_blocks.y;iy++)
			{
				int ix = 0;

				for (ix=0;ix<int(total_blocks.x/quato);ix++)
					yoloswag420blazeit360noscope<<<quato, BLOCK>>>(net.input_gpu, size, layer.rand_gpu, layer.probability, layer.scale, ix*quato, iy, iz);

				// if the iteration is not integer, run last time with fixed number blocks
				if (double(total_blocks.x) - quato * int(double(total_blocks.x)/quato) > 0)
					yoloswag420blazeit360noscope<<<total_blocks.x - quato * ix, BLOCK>>>(net.input_gpu, size, layer.rand_gpu, layer.probability, layer.scale, ix*quato, iy, iz);
			}
		}
	}
	else
	{
		yoloswag420blazeit360noscope<<<cuda_gridsize(size), BLOCK>>>(net.input_gpu, size, layer.rand_gpu, layer.probability, layer.scale, 0, 0, 0);
	}

    // yoloswag420blazeit360noscope<<<cuda_gridsize(size), BLOCK>>>(net.input_gpu, size, layer.rand_gpu, layer.probability, layer.scale, 0, 0, 0);
    check_error(cudaPeekAtLastError());
}

void backward_dropout_layer_gpu(dropout_layer layer, network net)
{
    if(!net.delta_gpu) return;
    int size = layer.inputs*layer.batch;

	if (VIRTUALGPU)
	{
		dim3 total_blocks = cuda_gridsize(size); int quato=QUATO;

		for (int iz=0;iz<total_blocks.z;iz++)
		{
			for (int iy=0;iy<total_blocks.y;iy++)
			{
				int ix = 0;

				for (ix=0;ix<int(total_blocks.x/quato);ix++)
					yoloswag420blazeit360noscope<<<quato, BLOCK>>>(net.delta_gpu, size, layer.rand_gpu, layer.probability, layer.scale, ix*quato, iy, iz);

				// if the iteration is not integer, run last time with fixed number blocks
				if (double(total_blocks.x) - quato * int(double(total_blocks.x)/quato) > 0)
					yoloswag420blazeit360noscope<<<total_blocks.x - quato * ix, BLOCK>>>(net.delta_gpu, size, layer.rand_gpu, layer.probability, layer.scale, ix*quato, iy, iz);
			}
		}
	}
	else
	{
		yoloswag420blazeit360noscope<<<cuda_gridsize(size), BLOCK>>>(net.delta_gpu, size, layer.rand_gpu, layer.probability, layer.scale, 0, 0, 0);
	}

    // yoloswag420blazeit360noscope<<<cuda_gridsize(size), BLOCK>>>(net.delta_gpu, size, layer.rand_gpu, layer.probability, layer.scale, 0, 0, 0);
    check_error(cudaPeekAtLastError());
}
