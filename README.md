# EdgeSlice

The source codes are for the paper "Q. Liu, T. Han, E. Moges, “EdgeSlice: Slicing Wireless Edge Computing Network with Decentralized Deep Reinforcement Learning”, in IEEE International Conference on Distributed Computing Systems (ICDCS), Singapore, Jul. 2020".

It consists of three components: radio access network (RAN), transportation network and the edge computing servers.

The RAN implementation uses OpenAirInterface and OpenAir-CN, where our code virtualized the radio resource (physical reource blocks) and provide corresponding API for resource allocation.
The transportation network implementation uses OpenDayLight and OpenFlow switches, where our code virtualized the transport resource (bandwidth) and provide corresponding API for resource allocation.
The edge computing server implementation uses the Darknet object detection framework (YOLO), where our code virtualized the GPU computing resource (parallel threads) and provide corresponding API for resource allocation.

For detailed system build instructions, please refer to my email(qliu12@uncc.edu).
