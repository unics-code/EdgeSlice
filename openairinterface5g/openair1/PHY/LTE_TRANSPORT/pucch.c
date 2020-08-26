/*
 * Licensed to the OpenAirInterface (OAI) Software Alliance under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The OpenAirInterface Software Alliance licenses this file to You under
 * the OAI Public License, Version 1.1  (the "License"); you may not use this file
 * except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.openairinterface.org/?page_id=698
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *-------------------------------------------------------------------------------
 * For more information about the OpenAirInterface (OAI) Software Alliance:
 *      contact@openairinterface.org
 */

/*! \file PHY/LTE_TRANSPORT/pucch.c
* \brief Top-level routines for generating and decoding the PUCCH physical channel V8.6 2009-03
* \author R. Knopp
* \date 2011
* \version 0.1
* \company Eurecom
* \email: knopp@eurecom.fr
* \note
* \warning
*/
#include "PHY/defs.h"
#include "PHY/extern.h" 
#include "LAYER2/MAC/extern.h"

#include "UTIL/LOG/log.h"
#include "UTIL/LOG/vcd_signal_dumper.h"

#include "T.h"

//uint8_t ncs_cell[20][7];
//#define DEBUG_PUCCH_TX
//#define DEBUG_PUCCH_RX

int16_t cfo_pucch_np[24*7] = {20787,-25330,27244,-18205,31356,-9512,32767,0,31356,9511,27244,18204,20787,25329,
                              27244,-18205,30272,-12540,32137,-6393,32767,0,32137,6392,30272,12539,27244,18204,
                              31356,-9512,32137,-6393,32609,-3212,32767,0,32609,3211,32137,6392,31356,9511,
                              32767,0,32767,0,32767,0,32767,0,32767,0,32767,0,32767,0,
                              31356,9511,32137,6392,32609,3211,32767,0,32609,-3212,32137,-6393,31356,-9512,
                              27244,18204,30272,12539,32137,6392,32767,0,32137,-6393,30272,-12540,27244,-18205,
                              20787,25329,27244,18204,31356,9511,32767,0,31356,-9512,27244,-18205,20787,-25330
                             };

int16_t cfo_pucch_ep[24*6] = {24278,-22005,29621,-14010,32412,-4808,32412,4807,29621,14009,24278,22004,
                              28897,-15447,31356,-9512,32609,-3212,32609,3211,31356,9511,28897,15446,
                              31785,-7962,32412,-4808,32727,-1608,32727,1607,32412,4807,31785,7961,
                              32767,0,32767,0,32767,0,32767,0,32767,0,32767,0,
                              31785,7961,32412,4807,32727,1607,32727,-1608,32412,-4808,31785,-7962,
                              28897,15446,31356,9511,32609,3211,32609,-3212,31356,-9512,28897,-15447,
                              24278,22004,29621,14009,32412,4807,32412,-4808,29621,-14010,24278,-22005
                             };


void init_ncs_cell(LTE_DL_FRAME_PARMS *frame_parms,uint8_t ncs_cell[20][7])
{

  uint8_t ns,l,reset=1,i,N_UL_symb;
  uint32_t x1,x2,j=0,s=0;

  N_UL_symb = (frame_parms->Ncp==0) ? 7 : 6;
  x2 = frame_parms->Nid_cell;

  for (ns=0; ns<20; ns++) {

    for (l=0; l<N_UL_symb; l++) {
      ncs_cell[ns][l]=0;

      for (i=0; i<8; i++) {
        if ((j%32) == 0) {
          s = lte_gold_generic(&x1,&x2,reset);
          //    printf("s %x\n",s);
          reset=0;
        }

        if (((s>>(j%32))&1)==1)
          ncs_cell[ns][l] += (1<<i);

        j++;
      }

#ifdef DEBUG_PUCCH_TX
      printf("[PHY] PUCCH ncs_cell init (j %d): Ns %d, l %d => ncs_cell %d\n",j,ns,l,ncs_cell[ns][l]);
#endif
    }

  }
}

int16_t alpha_re[12] = {32767, 28377, 16383,     0,-16384,  -28378,-32768,-28378,-16384,    -1, 16383, 28377};
int16_t alpha_im[12] = {0,     16383, 28377, 32767, 28377,   16383,     0,-16384,-28378,-32768,-28378,-16384};

int16_t W4[3][4] = {{32767, 32767, 32767, 32767},
  {32767,-32768, 32767,-32768},
  {32767,-32768,-32768, 32767}
};
int16_t W3_re[3][6] = {{32767, 32767, 32767},
  {32767,-16384,-16384},
  {32767,-16384,-16384}
};

int16_t W3_im[3][6] = {{0    ,0     ,0     },
  {0    , 28377,-28378},
  {0    ,-28378, 28377}
};

char pucch_format_string[6][20] = {"format 1\0","format 1a\0","format 1b\0","format 2\0","format 2a\0","format 2b\0"};

/* PUCCH format3 >> */
#define D_I             0
#define D_Q             1
#define D_IQDATA        2
#define D_NSLT1SF       2
#define D_NSYM1SLT      7
#define D_NSYM1SF       2*7
#define D_NSC1RB        12
#define D_NRB1PUCCH     2
#define D_NPUCCH_SF5    5
#define D_NPUCCH_SF4    4

uint8_t chcod_tbl[128][48] = { {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
  {1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1},
  {1, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1},
  {0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0},
  {0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0},
  {1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1},
  {1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1},
  {0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0},
  {0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0},
  {1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 1},
  {1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1},
  {0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0},
  {0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0},
  {1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1},
  {1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1},
  {0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0},
  {0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1},
  {1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0},
  {1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0},
  {0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1},
  {0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1},
  {1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0},
  {1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0},
  {0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1},
  {0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1},
  {1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0},
  {1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0},
  {0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1},
  {0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1},
  {1, 0, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0},
  {1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0},
  {0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 1},
  {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1},
  {1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0},
  {1, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0},
  {0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1},
  {0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1},
  {1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0},
  {1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0},
  {0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1},
  {0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1},
  {1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0},
  {1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0},
  {0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1},
  {0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1},
  {1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0},
  {1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 0},
  {0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1},
  {0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0},
  {1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1},
  {1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1},
  {0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0},
  {0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0},
  {1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1},
  {1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1},
  {0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0},
  {0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0},
  {1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1},
  {1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1},
  {0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0},
  {0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0},
  {1, 0, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1},
  {1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1},
  {0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0},
  {0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1},
  {1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0},
  {1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 0},
  {0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 1},
  {0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1},
  {1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0},
  {1, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0},
  {0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1},
  {0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1},
  {1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0},
  {1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0},
  {0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1},
  {0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1},
  {1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0},
  {1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0},
  {0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1},
  {0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0},
  {1, 1, 0, 1, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1},
  {1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1},
  {0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0},
  {0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0},
  {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1},
  {1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1},
  {0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0},
  {0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0},
  {1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1},
  {1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1},
  {0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0},
  {0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0},
  {1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1},
  {1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 1},
  {0, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 0},
  {0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0},
  {1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1},
  {1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1},
  {0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0},
  {0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0},
  {1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1},
  {1, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1},
  {0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0},
  {0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0},
  {1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1},
  {1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1},
  {0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0},
  {0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0},
  {1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 1},
  {1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1},
  {0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0},
  {0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1},
  {1, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0},
  {1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0},
  {0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 1},
  {0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1},
  {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0},
  {1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0},
  {0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1},
  {0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1},
  {1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0},
  {1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0},
  {0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1},
  {0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1},
  {1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0},
  {1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0},
  {0, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1} };

// W5_TBL
int16_t W5_fmt3_re[5][5] = { {32767, 32767, 32767, 32767, 32767},
  {32767, 10125, -26509, -26509, 10125},
  {32767, -26509, 10125, 10125, -26509},
  {32767, -26509, 10125, 10125, -26509},
  {32767, 10125, -26509, -26509, 10125} };

int16_t W5_fmt3_im[5][5] = { {0, 0, 0, 0, 0},
  {0, 31163, 19259, -19259, -31163},
  {0, 19259, -31163, 31163, -19259},
  {0, -19259, 31163, -31163, 19259},
  {0, -31163, -19259, 19259, 31163} };

int16_t W4_fmt3[4][4] = { {32767, 32767, 32767, 32767},
  {32767, -32767, 32767, -32767},
  {32767, 32767, -32767, -32767},
  {32767, -32767, -32767, 32767} };

// W2 TBL
int16_t W2[2] = {32767, 32767};

// e^j*pai*floor (ncs_cell(ns,l)/64)/2
int16_t RotTBL_re[4] = {32767, 0, -32767, 0};
int16_t RotTBL_im[4] = {0, 32767, 0, -32767};

//np4_tbl, np5_tbl
uint8_t Np5_TBL[5] = {0, 3, 6, 8, 10};
uint8_t Np4_TBL[4] = {0, 3, 6, 9};

// alpha_TBL
int16_t alphaTBL_re[12] = {32767, 28377, 16383, 0, -16383, -28377, -32767, -28377, -16383, 0, 16383, 28377};
int16_t alphaTBL_im[12] = {0, 16383, 28377, 32767, 28377, 16383, 0, -16383, -28377, -32767, -28377, -16383};

/* PUCCH format3 << */

void generate_pucch1x(int32_t **txdataF,
		      LTE_DL_FRAME_PARMS *frame_parms,
		      uint8_t ncs_cell[20][7],
		      PUCCH_FMT_t fmt,
		      PUCCH_CONFIG_DEDICATED *pucch_config_dedicated,
		      uint16_t n1_pucch,
		      uint8_t shortened_format,
		      uint8_t *payload,
		      int16_t amp,
		      uint8_t subframe)
{

  uint32_t u,v,n;
  uint32_t z[12*14],*zptr;
  int16_t d0;
  uint8_t ns,N_UL_symb,nsymb,n_oc,n_oc0,n_oc1;
  uint8_t c = (frame_parms->Ncp==0) ? 3 : 2;
  uint16_t nprime,nprime0,nprime1;
  uint16_t i,j,re_offset,thres,h;
  uint8_t Nprime_div_deltaPUCCH_Shift,Nprime,d;
  uint8_t m,l,refs;
  uint8_t n_cs,S,alpha_ind,rem;
  int16_t tmp_re,tmp_im,ref_re,ref_im,W_re=0,W_im=0;
  int32_t *txptr;
  uint32_t symbol_offset;

  uint8_t deltaPUCCH_Shift          = frame_parms->pucch_config_common.deltaPUCCH_Shift;
  uint8_t NRB2                      = frame_parms->pucch_config_common.nRB_CQI;
  uint8_t Ncs1                      = frame_parms->pucch_config_common.nCS_AN;
  uint8_t Ncs1_div_deltaPUCCH_Shift = Ncs1/deltaPUCCH_Shift;

  LOG_D(PHY,"generate_pucch Start [deltaPUCCH_Shift %d, NRB2 %d, Ncs1_div_deltaPUCCH_Shift %d, n1_pucch %d]\n", deltaPUCCH_Shift, NRB2, Ncs1_div_deltaPUCCH_Shift,n1_pucch);


  uint32_t u0 = (frame_parms->Nid_cell + frame_parms->pusch_config_common.ul_ReferenceSignalsPUSCH.grouphop[subframe<<1]) % 30;
  uint32_t u1 = (frame_parms->Nid_cell + frame_parms->pusch_config_common.ul_ReferenceSignalsPUSCH.grouphop[1+(subframe<<1)]) % 30;
  uint32_t v0=frame_parms->pusch_config_common.ul_ReferenceSignalsPUSCH.seqhop[subframe<<1];
  uint32_t v1=frame_parms->pusch_config_common.ul_ReferenceSignalsPUSCH.seqhop[1+(subframe<<1)];

  if ((deltaPUCCH_Shift==0) || (deltaPUCCH_Shift>3)) {
    printf("[PHY] generate_pucch: Illegal deltaPUCCH_shift %d (should be 1,2,3)\n",deltaPUCCH_Shift);
    return;
  }

  if (Ncs1_div_deltaPUCCH_Shift > 7) {
    printf("[PHY] generate_pucch: Illegal Ncs1_div_deltaPUCCH_Shift %d (should be 0...7)\n",Ncs1_div_deltaPUCCH_Shift);
    return;
  }

  zptr = z;
  thres = (c*Ncs1_div_deltaPUCCH_Shift);
  Nprime_div_deltaPUCCH_Shift = (n1_pucch < thres) ? Ncs1_div_deltaPUCCH_Shift : (12/deltaPUCCH_Shift);
  Nprime = Nprime_div_deltaPUCCH_Shift * deltaPUCCH_Shift;

#ifdef DEBUG_PUCCH_TX
  printf("[PHY] PUCCH: cNcs1/deltaPUCCH_Shift %d, Nprime %d, n1_pucch %d\n",thres,Nprime,n1_pucch);
#endif

  LOG_D(PHY,"[PHY] PUCCH: n1_pucch %d, thres %d Ncs1_div_deltaPUCCH_Shift %d (12/deltaPUCCH_Shift) %d Nprime_div_deltaPUCCH_Shift %d \n",
		              n1_pucch, thres, Ncs1_div_deltaPUCCH_Shift, (int)(12/deltaPUCCH_Shift), Nprime_div_deltaPUCCH_Shift);
  LOG_D(PHY,"[PHY] PUCCH: deltaPUCCH_Shift %d, Nprime %d\n",deltaPUCCH_Shift,Nprime);


  N_UL_symb = (frame_parms->Ncp==0) ? 7 : 6;

  if (n1_pucch < thres)
    nprime0=n1_pucch;
  else
    nprime0 = (n1_pucch - thres)%(12*c/deltaPUCCH_Shift);

  if (n1_pucch >= thres)
    nprime1= ((c*(nprime0+1))%((12*c/deltaPUCCH_Shift)+1))-1;
  else {
    d = (frame_parms->Ncp==0) ? 2 : 0;
    h= (nprime0+d)%(c*Nprime_div_deltaPUCCH_Shift);
#ifdef DEBUG_PUCCH_TX
    printf("[PHY] PUCCH: h %d, d %d\n",h,d);
#endif
    nprime1 = (h/c) + (h%c)*Nprime_div_deltaPUCCH_Shift;
  }

#ifdef DEBUG_PUCCH_TX
  printf("[PHY] PUCCH: nprime0 %d nprime1 %d, %s, payload (%d,%d)\n",nprime0,nprime1,pucch_format_string[fmt],payload[0],payload[1]);
#endif

  n_oc0 = nprime0/Nprime_div_deltaPUCCH_Shift;

  if (frame_parms->Ncp==1)
    n_oc0<<=1;

  n_oc1 = nprime1/Nprime_div_deltaPUCCH_Shift;

  if (frame_parms->Ncp==1)  // extended CP
    n_oc1<<=1;

#ifdef DEBUG_PUCCH_TX
  printf("[PHY] PUCCH: noc0 %d noc1 %d\n",n_oc0,n_oc1);
#endif

  nprime=nprime0;
  n_oc  =n_oc0;

  // loop over 2 slots
  for (ns=(subframe<<1),u=u0,v=v0; ns<(2+(subframe<<1)); ns++,u=u1,v=v1) {

    if ((nprime&1) == 0)
      S=0;  // 1
    else
      S=1;  // j

    //loop over symbols in slot
    for (l=0; l<N_UL_symb; l++) {
      // Compute n_cs (36.211 p. 18)
      n_cs = ncs_cell[ns][l];

      if (frame_parms->Ncp==0) { // normal CP
        n_cs = ((uint16_t)n_cs + (nprime*deltaPUCCH_Shift + (n_oc%deltaPUCCH_Shift))%Nprime)%12;
      } else {
        n_cs = ((uint16_t)n_cs + (nprime*deltaPUCCH_Shift + (n_oc>>1))%Nprime)%12;
      }


      refs=0;

      // Comput W_noc(m) (36.211 p. 19)
      if ((ns==(1+(subframe<<1))) && (shortened_format==1)) {  // second slot and shortened format

        if (l<2) {                                         // data
          W_re=W3_re[n_oc][l];
          W_im=W3_im[n_oc][l];
        } else if ((l<N_UL_symb-2)&&(frame_parms->Ncp==0)) { // reference and normal CP
          W_re=W3_re[n_oc][l-2];
          W_im=W3_im[n_oc][l-2];
          refs=1;
        } else if ((l<N_UL_symb-2)&&(frame_parms->Ncp==1)) { // reference and extended CP
          W_re=W4[n_oc][l-2];
          W_im=0;
          refs=1;
        } else if ((l>=N_UL_symb-2)) {                      // data
          W_re=W3_re[n_oc][l-N_UL_symb+4];
          W_im=W3_im[n_oc][l-N_UL_symb+4];
        }
      } else {
        if (l<2) {                                         // data
          W_re=W4[n_oc][l];
          W_im=0;
        } else if ((l<N_UL_symb-2)&&(frame_parms->Ncp==0)) { // reference and normal CP
          W_re=W3_re[n_oc][l-2];
          W_im=W3_im[n_oc][l-2];
          refs=1;
        } else if ((l<N_UL_symb-2)&&(frame_parms->Ncp==1)) { // reference and extended CP
          W_re=W4[n_oc][l-2];
          W_im=0;
          refs=1;
        } else if ((l>=N_UL_symb-2)) {                     // data
          W_re=W4[n_oc][l-N_UL_symb+4];
          W_im=0;
        }
      }

      // multiply W by S(ns) (36.211 p.17). only for data, reference symbols do not have this factor
      if ((S==1)&&(refs==0)) {
        tmp_re = W_re;
        W_re = -W_im;
        W_im = tmp_re;
      }

#ifdef DEBUG_PUCCH_TX
      printf("[PHY] PUCCH: ncs[%d][%d]=%d, W_re %d, W_im %d, S %d, refs %d\n",ns,l,n_cs,W_re,W_im,S,refs);
#endif
      alpha_ind=0;
      // compute output sequence

      for (n=0; n<12; n++) {

        // this is r_uv^alpha(n)
        tmp_re = (int16_t)(((int32_t)alpha_re[alpha_ind] * ul_ref_sigs[u][v][0][n<<1] - (int32_t)alpha_im[alpha_ind] * ul_ref_sigs[u][v][0][1+(n<<1)])>>15);
        tmp_im = (int16_t)(((int32_t)alpha_re[alpha_ind] * ul_ref_sigs[u][v][0][1+(n<<1)] + (int32_t)alpha_im[alpha_ind] * ul_ref_sigs[u][v][0][n<<1])>>15);

        // this is S(ns)*w_noc(m)*r_uv^alpha(n)
        ref_re = (tmp_re*W_re - tmp_im*W_im)>>15;
        ref_im = (tmp_re*W_im + tmp_im*W_re)>>15;

        if ((l<2)||(l>=(N_UL_symb-2))) { //these are PUCCH data symbols
          switch (fmt) {
          case pucch_format1:   //OOK 1-bit

            ((int16_t *)&zptr[n])[0] = ((int32_t)amp*ref_re)>>15;
            ((int16_t *)&zptr[n])[1] = ((int32_t)amp*ref_im)>>15;

            break;

          case pucch_format1a:  //BPSK 1-bit
            d0 = (payload[0]&1)==0 ? amp : -amp;
            ((int16_t *)&zptr[n])[0] = ((int32_t)d0*ref_re)>>15;
            ((int16_t *)&zptr[n])[1] = ((int32_t)d0*ref_im)>>15;
            //      printf("d0 %d\n",d0);
            break;

          case pucch_format1b:  //QPSK 2-bits (Table 5.4.1-1 from 36.211, pg. 18)
            if (((payload[0]&1)==0) && ((payload[1]&1)==0))  {// 1
              ((int16_t *)&zptr[n])[0] = ((int32_t)amp*ref_re)>>15;
              ((int16_t *)&zptr[n])[1] = ((int32_t)amp*ref_im)>>15;
            } else if (((payload[0]&1)==0) && ((payload[1]&1)==1))  { // -j
              ((int16_t *)&zptr[n])[0] = ((int32_t)amp*ref_im)>>15;
              ((int16_t *)&zptr[n])[1] = (-(int32_t)amp*ref_re)>>15;
            } else if (((payload[0]&1)==1) && ((payload[1]&1)==0))  { // j
              ((int16_t *)&zptr[n])[0] = (-(int32_t)amp*ref_im)>>15;
              ((int16_t *)&zptr[n])[1] = ((int32_t)amp*ref_re)>>15;
            } else  { // -1
              ((int16_t *)&zptr[n])[0] = (-(int32_t)amp*ref_re)>>15;
              ((int16_t *)&zptr[n])[1] = (-(int32_t)amp*ref_im)>>15;
            }

            break;

          case pucch_format2:
          case pucch_format2a:
          case pucch_format2b:
            AssertFatal(1==0,"should not go here\n");
            break;

          case pucch_format3:
            fprintf(stderr, "PUCCH format 3 not handled\n");
            abort();
          } // switch fmt
        } else { // These are PUCCH reference symbols

          ((int16_t *)&zptr[n])[0] = ((int32_t)amp*ref_re)>>15;
          ((int16_t *)&zptr[n])[1] = ((int32_t)amp*ref_im)>>15;
          //    printf("ref\n");
        }

#ifdef DEBUG_PUCCH_TX
        printf("[PHY] PUCCH subframe %d z(%d,%d) => %d,%d, alpha(%d) => %d,%d\n",subframe,l,n,((int16_t *)&zptr[n])[0],((int16_t *)&zptr[n])[1],
            alpha_ind,alpha_re[alpha_ind],alpha_im[alpha_ind]);
#endif
        alpha_ind = (alpha_ind + n_cs)%12;
      } // n

      zptr+=12;
    } // l

    nprime=nprime1;
    n_oc  =n_oc1;
  } // ns

  rem = ((((12*Ncs1_div_deltaPUCCH_Shift)>>3)&7)>0) ? 1 : 0;

  m = (n1_pucch < thres) ? NRB2 : (((n1_pucch-thres)/(12*c/deltaPUCCH_Shift))+NRB2+((deltaPUCCH_Shift*Ncs1_div_deltaPUCCH_Shift)>>3)+rem);

#ifdef DEBUG_PUCCH_TX
  printf("[PHY] PUCCH: m %d\n",m);
#endif
  nsymb = N_UL_symb<<1;

  //for (j=0,l=0;l<(nsymb-1);l++) {
  for (j=0,l=0; l<(nsymb); l++) {
    if ((l<(nsymb>>1)) && ((m&1) == 0))
      re_offset = (m*6) + frame_parms->first_carrier_offset;
    else if ((l<(nsymb>>1)) && ((m&1) == 1))
      re_offset = frame_parms->first_carrier_offset + (frame_parms->N_RB_DL - (m>>1) - 1)*12;
    else if ((m&1) == 0)
      re_offset = frame_parms->first_carrier_offset + (frame_parms->N_RB_DL - (m>>1) - 1)*12;
    else
      re_offset = ((m-1)*6) + frame_parms->first_carrier_offset;

    if (re_offset > frame_parms->ofdm_symbol_size)
      re_offset -= (frame_parms->ofdm_symbol_size);

    symbol_offset = (unsigned int)frame_parms->ofdm_symbol_size*(l+(subframe*nsymb));
    txptr = &txdataF[0][symbol_offset];

    for (i=0; i<12; i++,j++) {
      txptr[re_offset++] = z[j];

      if (re_offset==frame_parms->ofdm_symbol_size)
        re_offset = 0;

#ifdef DEBUG_PUCCH_TX
      printf("[PHY] PUCCH subframe %d (%d,%d,%d,%d) => %d,%d\n",subframe,l,i,re_offset-1,m,((int16_t *)&z[j])[0],((int16_t *)&z[j])[1]);
#endif
    }
  }

}

void generate_pucch_emul(PHY_VARS_UE *ue,
			 UE_rxtx_proc_t *proc,
                         PUCCH_FMT_t format,
                         uint8_t ncs1,
                         uint8_t *pucch_payload,
                         uint8_t sr)

{

  int subframe = proc->subframe_tx;

  UE_transport_info[ue->Mod_id][ue->CC_id].cntl.pucch_flag    = format;
  UE_transport_info[ue->Mod_id][ue->CC_id].cntl.pucch_Ncs1    = ncs1;


  UE_transport_info[ue->Mod_id][ue->CC_id].cntl.sr            = sr;
  // the value of ue->pucch_sel[subframe] is set by get_n1_pucch
  UE_transport_info[ue->Mod_id][ue->CC_id].cntl.pucch_sel      = ue->pucch_sel[subframe];

  // LOG_I(PHY,"subframe %d emu tx pucch_sel is %d sr is %d \n", subframe, UE_transport_info[ue->Mod_id].cntl.pucch_sel, sr);

  if (format == pucch_format1a) {

    ue->pucch_payload[0] = pucch_payload[0];
    UE_transport_info[ue->Mod_id][ue->CC_id].cntl.pucch_payload = pucch_payload[0];
  } else if (format == pucch_format1b) {
    ue->pucch_payload[0] = pucch_payload[0] + (pucch_payload[1]<<1);
    UE_transport_info[ue->Mod_id][ue->CC_id].cntl.pucch_payload = pucch_payload[0] + (pucch_payload[1]<<1);
  } else if (format == pucch_format1) {
    //    LOG_D(PHY,"[UE %d] Frame %d subframe %d Generating PUCCH for SR %d\n",ue->Mod_id,proc->frame_tx,subframe,sr);
  }

  ue->sr[subframe] = sr;

}


inline void pucch2x_scrambling(LTE_DL_FRAME_PARMS *fp,int subframe,uint16_t rnti,uint32_t B,uint8_t *btilde) __attribute__((always_inline));
inline void pucch2x_scrambling(LTE_DL_FRAME_PARMS *fp,int subframe,uint16_t rnti,uint32_t B,uint8_t *btilde) {

  uint32_t x1, x2, s=0;
  int i;
  uint8_t c;

  x2 = (rnti) + ((uint32_t)(1+subframe)<<16)*(1+(fp->Nid_cell<<1)); //this is c_init in 36.211 Sec 6.3.1
  s = lte_gold_generic(&x1, &x2, 1);
  for (i=0;i<19;i++) {
    c = (uint8_t)((s>>i)&1);
    btilde[i] = (((B>>i)&1) ^ c);
  }
}

inline void pucch2x_modulation(uint8_t *btilde,int16_t *d,int16_t amp) __attribute__((always_inline));
inline void pucch2x_modulation(uint8_t *btilde,int16_t *d,int16_t amp) {

  int i;

  for (i=0;i<20;i++) 
    d[i] = btilde[i] == 1 ? -amp : amp;

}



uint32_t pucch_code[13] = {0xFFFFF,0x5A933,0x10E5A,0x6339C,0x73CE0,
			   0xFFC00,0xD8E64,0x4F6B0,0x218EC,0x1B746,
			   0x0FFFF,0x33FFF,0x3FFFC};


void generate_pucch2x(int32_t **txdataF,
		      LTE_DL_FRAME_PARMS *fp,
		      uint8_t ncs_cell[20][7],
		      PUCCH_FMT_t fmt,
		      PUCCH_CONFIG_DEDICATED *pucch_config_dedicated,
		      uint16_t n2_pucch,
		      uint8_t *payload,
		      int A,
		      int B2,
		      int16_t amp,
		      uint8_t subframe,
		      uint16_t rnti) {

  int i,j;
  uint32_t B=0;
  uint8_t btilde[20];
  int16_t d[22];
  uint8_t deltaPUCCH_Shift          = fp->pucch_config_common.deltaPUCCH_Shift;
  uint8_t NRB2                      = fp->pucch_config_common.nRB_CQI;
  uint8_t Ncs1                      = fp->pucch_config_common.nCS_AN;

  uint32_t u0 = fp->pucch_config_common.grouphop[subframe<<1];
  uint32_t u1 = fp->pucch_config_common.grouphop[1+(subframe<<1)];
  uint32_t v0 = fp->pusch_config_common.ul_ReferenceSignalsPUSCH.seqhop[subframe<<1];
  uint32_t v1 = fp->pusch_config_common.ul_ReferenceSignalsPUSCH.seqhop[1+(subframe<<1)];

  uint32_t z[12*14],*zptr;
  uint32_t u,v,n;
  uint8_t ns,N_UL_symb,nsymb_slot0,nsymb_pertti;
  uint32_t nprime,l,n_cs;
  int alpha_ind,data_ind;
  int16_t ref_re,ref_im;
  int m,re_offset,symbol_offset;
  int32_t *txptr;

  if ((deltaPUCCH_Shift==0) || (deltaPUCCH_Shift>3)) {
    printf("[PHY] generate_pucch: Illegal deltaPUCCH_shift %d (should be 1,2,3)\n",deltaPUCCH_Shift);
    return;
  }

  if (Ncs1 > 7) {
    printf("[PHY] generate_pucch: Illegal Ncs1 %d (should be 0...7)\n",Ncs1);
    return;
  }

  // pucch2x_encoding
  for (i=0;i<A;i++)
    if ((*payload & (1<<i)) > 0)
      B=B^pucch_code[i];

  // scrambling
  pucch2x_scrambling(fp,subframe,rnti,B,btilde);
  // modulation
  pucch2x_modulation(btilde,d,amp);

  // add extra symbol for 2a/2b
  d[20]=0;
  d[21]=0;
  if (fmt==pucch_format2a)
    d[20] = (B2 == 0) ? amp : -amp;
  else if (fmt==pucch_format2b) {
    switch (B2) {
    case 0:
      d[20] = amp;
      break;
    case 1:
      d[21] = -amp;
      break;
    case 2:
      d[21] = amp;
      break;
    case 3:
      d[20] = -amp;
      break;
    default:
      AssertFatal(1==0,"Illegal modulation symbol %d for PUCCH %s\n",B2,pucch_format_string[fmt]);
      break;
    }
  }


#ifdef DEBUG_PUCCH_TX
  printf("[PHY] PUCCH2x: n2_pucch %d\n",n2_pucch);
#endif

  N_UL_symb = (fp->Ncp==0) ? 7 : 6;
  data_ind  = 0;
  zptr      = z;
  nprime    = 0;
  for (ns=(subframe<<1),u=u0,v=v0; ns<(2+(subframe<<1)); ns++,u=u1,v=v1) {

    if ((ns&1) == 0)
        nprime = (n2_pucch < 12*NRB2) ?
                n2_pucch % 12 :
                (n2_pucch+Ncs1 + 1)%12;
    else {
        nprime = (n2_pucch < 12*NRB2) ?
                ((12*(nprime+1)) % 13)-1 :
                (10-n2_pucch)%12;
    }
    //loop over symbols in slot
    for (l=0; l<N_UL_symb; l++) {
      // Compute n_cs (36.211 p. 18)
      n_cs = (ncs_cell[ns][l]+nprime)%12;

      alpha_ind = 0;
      for (n=0; n<12; n++)
      {
          // this is r_uv^alpha(n)
          ref_re = (int16_t)(((int32_t)alpha_re[alpha_ind] * ul_ref_sigs[u][v][0][n<<1] - (int32_t)alpha_im[alpha_ind] * ul_ref_sigs[u][v][0][1+(n<<1)])>>15);
          ref_im = (int16_t)(((int32_t)alpha_re[alpha_ind] * ul_ref_sigs[u][v][0][1+(n<<1)] + (int32_t)alpha_im[alpha_ind] * ul_ref_sigs[u][v][0][n<<1])>>15);

          if ((l!=1)&&(l!=5)) { //these are PUCCH data symbols
              ((int16_t *)&zptr[n])[0] = ((int32_t)d[data_ind]*ref_re - (int32_t)d[data_ind+1]*ref_im)>>15;
              ((int16_t *)&zptr[n])[1] = ((int32_t)d[data_ind]*ref_im + (int32_t)d[data_ind+1]*ref_re)>>15;
              //LOG_I(PHY,"slot %d ofdm# %d ==> d[%d,%d] \n",ns,l,data_ind,n);
          }
          else {
              if ((l==1) || ( (l==5) && (fmt==pucch_format2) ))
              {
                  ((int16_t *)&zptr[n])[0] = ((int32_t)amp*ref_re>>15);
                  ((int16_t *)&zptr[n])[1] = ((int32_t)amp*ref_im>>15);
              }
              // l == 5 && pucch format 2a
              else if (fmt==pucch_format2a)
              {
                  ((int16_t *)&zptr[n])[0] = ((int32_t)d[20]*ref_re>>15);
                  ((int16_t *)&zptr[n])[1] = ((int32_t)d[21]*ref_im>>15);
              }
              // l == 5 && pucch format 2b
              else if (fmt==pucch_format2b)
              {
                  ((int16_t *)&zptr[n])[0] = ((int32_t)d[20]*ref_re>>15);
                  ((int16_t *)&zptr[n])[1] = ((int32_t)d[21]*ref_im>>15);
              }
          } // l==1 || l==5
      alpha_ind = (alpha_ind + n_cs)%12;
      } // n
      zptr+=12;

      if ((l!=1)&&(l!=5))  //these are PUCCH data symbols so increment data index
	     data_ind+=2;
    } // l
  } //ns

  m = n2_pucch/12;

#ifdef DEBUG_PUCCH_TX
  LOG_D(PHY,"[PHY] PUCCH: n2_pucch %d m %d\n",n2_pucch,m);
#endif

  nsymb_slot0  = ((fp->Ncp==0) ? 7 : 6);
  nsymb_pertti = nsymb_slot0 << 1;

  //nsymb = nsymb_slot0<<1;

  //for (j=0,l=0;l<(nsymb-1);l++) {
  for (j=0,l=0; l<(nsymb_pertti); l++) {

    if ((l<nsymb_slot0) && ((m&1) == 0))
      re_offset = (m*6) + fp->first_carrier_offset;
    else if ((l<nsymb_slot0) && ((m&1) == 1))
      re_offset = fp->first_carrier_offset + (fp->N_RB_DL - (m>>1) - 1)*12;
    else if ((m&1) == 0)
      re_offset = fp->first_carrier_offset + (fp->N_RB_DL - (m>>1) - 1)*12;
    else
      re_offset = ((m-1)*6) + fp->first_carrier_offset;

    if (re_offset > fp->ofdm_symbol_size)
      re_offset -= (fp->ofdm_symbol_size);



    symbol_offset = (unsigned int)fp->ofdm_symbol_size*(l+(subframe*nsymb_pertti));
    txptr = &txdataF[0][symbol_offset];

    //LOG_I(PHY,"ofdmSymb %d/%d, firstCarrierOffset %d, symbolOffset[sfn %d] %d, reOffset %d, &txptr: %x \n", l, nsymb, fp->first_carrier_offset, subframe, symbol_offset, re_offset, &txptr[0]);

    for (i=0; i<12; i++,j++) {
      txptr[re_offset] = z[j];

      re_offset++;

      if (re_offset==fp->ofdm_symbol_size)
          re_offset -= (fp->ofdm_symbol_size);

#ifdef DEBUG_PUCCH_TX
      LOG_D(PHY,"[PHY] PUCCH subframe %d (%d,%d,%d,%d) => %d,%d\n",subframe,l,i,re_offset-1,m,((int16_t *)&z[j])[0],((int16_t *)&z[j])[1]);
#endif
    }
  }
}

/* PUCCH format3 >> */
/* DFT */
void pucchfmt3_Dft( int16_t *x, int16_t *y )
{
  int16_t i, k;
  int16_t tmp[2];
  int16_t calctmp[D_NSC1RB*2]={0};

  for (i=0; i<D_NSC1RB; i++) {
    for(k=0; k<D_NSC1RB; k++) {
      tmp[0] = alphaTBL_re[(12-((i*k)%12))%12];
      tmp[1] = alphaTBL_im[(12-((i*k)%12))%12];

      calctmp[2*i] += (((int32_t)x[2*k] * tmp[0] - (int32_t)x[2*k+1] * tmp[1])>>15);
      calctmp[2*i+1] += (((int32_t)x[2*k+1] * tmp[0] + (int32_t)x[2*k] * tmp[1])>>15);
    }
    y[2*i] = (int16_t)( (double) calctmp[2*i] / sqrt(D_NSC1RB));
    y[2*i+1] = (int16_t)((double) calctmp[2*i+1] / sqrt(D_NSC1RB));
  }
}

void generate_pucch3x(int32_t **txdataF,
                    LTE_DL_FRAME_PARMS *frame_parms,
                    uint8_t ncs_cell[20][7],
                    PUCCH_FMT_t fmt,
                    PUCCH_CONFIG_DEDICATED *pucch_config_dedicated,
                    uint16_t n3_pucch,
                    uint8_t shortened_format,
                    uint8_t *payload,
                    int16_t amp,
                    uint8_t subframe,
                    uint16_t rnti)
{

  uint32_t u, v;
  uint16_t i, j, re_offset;
  uint32_t z[12*14], *zptr;
  uint32_t y_tilda[12*14]={}, *y_tilda_ptr;
  uint8_t ns, nsymb, n_oc, n_oc0, n_oc1;
  uint8_t N_UL_symb = (frame_parms->Ncp==0) ? 7 : 6;
  uint8_t m, l;
  uint8_t n_cs;
  int16_t tmp_re, tmp_im, W_re=0, W_im=0;
  int32_t *txptr;
  uint32_t symbol_offset;
  
  uint32_t u0 = (frame_parms->Nid_cell + frame_parms->pusch_config_common.ul_ReferenceSignalsPUSCH.grouphop[subframe<<1]) % 30;
  uint32_t u1 = (frame_parms->Nid_cell + frame_parms->pusch_config_common.ul_ReferenceSignalsPUSCH.grouphop[1+(subframe<<1)]) % 30;
  uint32_t v0=frame_parms->pusch_config_common.ul_ReferenceSignalsPUSCH.seqhop[subframe<<1];
  uint32_t v1=frame_parms->pusch_config_common.ul_ReferenceSignalsPUSCH.seqhop[1+(subframe<<1)];

  // variables for channel coding
  uint8_t chcod_tbl_idx = 0;
  //uint8_t chcod_dt[48] = {};

  // variables for Scrambling
  uint32_t cinit = 0;
  uint32_t x1;
  uint32_t s,s0,s1;
  uint8_t  C[48] ={};
  uint8_t  scr_dt[48]={};

  // variables for Modulation
  int16_t d_re[24]={};
  int16_t d_im[24]={};

  // variables for orthogonal sequence selection
  uint8_t N_PUCCH_SF0 = 5;
  uint8_t N_PUCCH_SF1 = (shortened_format==0)? 5:4;
  uint8_t first_slot  = 0;
  int16_t rot_re=0;
  int16_t rot_im=0;

  uint8_t dt_offset;
  uint8_t sym_offset;
  int16_t y_re[14][12]; //={0};
  int16_t y_im[14][12]; //={0};

  // DMRS
  uint8_t alpha_idx=0;
  uint8_t m_alpha_idx=0;

  // TODO
  // "SR+ACK/NACK" length is only 7 bits.
  // This restriction will be lifted in the future.
  // "CQI/PMI/RI+ACK/NACK" will be supported in the future.

    // Channel Coding
    for (uint8_t i=0; i<7; i++) {
      chcod_tbl_idx += (payload[i]<<i); 
    }

    // Scrambling
    cinit = (subframe + 1) * ((2 * frame_parms->Nid_cell + 1)<<16) + rnti;
    s0 = lte_gold_generic(&x1,&cinit,1);
    s1 = lte_gold_generic(&x1,&cinit,0);

    for (i=0; i<48; i++) {
      s = (i<32)? s0:s1;
      j = (i<32)? i:(i-32);
      C[i] = ((s>>j)&1);
    }

    for (i=0; i<48; i++) {
      scr_dt[i] = chcod_tbl[chcod_tbl_idx][i] ^ C[i];
    }

    // Modulation
    for (uint8_t i=0; i<48; i+=2){
      if (scr_dt[i]==0 && scr_dt[i+1]==0){
        d_re[ i>>1] = ((ONE_OVER_SQRT2_Q15 * amp) >>15);
        d_im[ i>>1] = ((ONE_OVER_SQRT2_Q15 * amp) >>15);
      } else if (scr_dt[i]==0 && scr_dt[i+1]==1) {
        d_re[ i>>1] = ((ONE_OVER_SQRT2_Q15 * amp) >>15);
        d_im[ i>>1] = -1 * ((ONE_OVER_SQRT2_Q15 * amp) >>15);
      } else if (scr_dt[i]==1 && scr_dt[i+1]==0) {
        d_re[ i>>1] = -1 * ((ONE_OVER_SQRT2_Q15 * amp)>>15);
        d_im[ i>>1] = ((ONE_OVER_SQRT2_Q15 * amp)>>15);
      } else if (scr_dt[i]==1 && scr_dt[i+1]==1) {
        d_re[ i>>1] = -1 * ((ONE_OVER_SQRT2_Q15 * amp)>>15);
        d_im[ i>>1] = -1 * ((ONE_OVER_SQRT2_Q15 * amp)>>15);
      } else {
        //***log Modulation Error!
      }
    }

    // Calculate Orthogonal Sequence index
    n_oc0 = n3_pucch % N_PUCCH_SF1;
    if (N_PUCCH_SF1 == 5) {
      n_oc1 = (3 * n_oc0) % N_PUCCH_SF1;
    } else {
      n_oc1 = n_oc0 % N_PUCCH_SF1;
    }

    y_tilda_ptr = y_tilda;
    zptr = z;

    // loop over 2 slots
    for (ns=(subframe<<1), u=u0, v=v0; ns<(2+(subframe<<1)); ns++, u=u1, v=v1) {
      first_slot = (ns==(subframe<<1))?1:0;

      //loop over symbols in slot
      for (l=0; l<N_UL_symb; l++) {
        rot_re = RotTBL_re[(uint8_t) ncs_cell[ns][l]/64] ;
        rot_im = RotTBL_im[(uint8_t) ncs_cell[ns][l]/64] ;

        // Comput W_noc(m) (36.211 p. 19)
        if ( first_slot == 0 && shortened_format==1) {  // second slot and shortened format
          n_oc = n_oc1;

          if (l<1) {                                         // data
            W_re=W4_fmt3[n_oc][l];
            W_im=0;
          } else if (l==1) {                                  // DMRS
            W_re=W2[0];
            W_im=0;
          } else if (l>=2 && l<5) {                          // data
            W_re=W4_fmt3[n_oc][l-1];
            W_im=0;
          } else if (l==5) {                                 // DMRS
            W_re=W2[1];
            W_im=0;
          } else if ((l>=N_UL_symb-2)) {                      // data
            ;
          } else {
            //***log W Select Error!
          }
        } else {
          if (first_slot == 1) {                       // 1st slot or 2nd slot and not shortened
            n_oc=n_oc0;
          } else {
            n_oc=n_oc1;
          }

          if (l<1) {                                         // data
            W_re=W5_fmt3_re[n_oc][l];
            W_im=W5_fmt3_im[n_oc][l];
          } else if (l==1) {                                  // DMRS
            W_re=W2[0];
            W_im=0;
          } else if (l>=2 && l<5) {                          // data
            W_re=W5_fmt3_re[n_oc][l-1];
            W_im=W5_fmt3_im[n_oc][l-1];
          } else if (l==5) {                                 // DMRS
            W_re=W2[1];
            W_im=0;
          } else if ((l>=N_UL_symb-1)) {                     // data
            W_re=W5_fmt3_re[n_oc][l-N_UL_symb+5];
            W_im=W5_fmt3_im[n_oc][l-N_UL_symb+5];
          } else {
            //***log W Select Error!
          }
        }  // W Selection end

        // Compute n_cs (36.211 p. 18)
        n_cs = ncs_cell[ns][l];
        if (N_PUCCH_SF1 == 5) {
          alpha_idx = (n_cs + Np5_TBL[n_oc]) % 12;
        } else {
          alpha_idx = (n_cs + Np4_TBL[n_oc]) % 12;
        }

        // generate pucch data
        dt_offset = (first_slot == 1) ? 0:12;
        sym_offset = (first_slot == 1) ? 0:7;

        for (i=0; i<12; i++) {
          // Calculate yn(i) 
          tmp_re = (((int32_t) (W_re*rot_re - W_im*rot_im)) >>15);
          tmp_im = (((int32_t) (W_re*rot_im + W_im*rot_re)) >>15);
          y_re[l+sym_offset][i] = (((int32_t) (tmp_re*d_re[i+dt_offset] - tmp_im*d_im[i+dt_offset]))>>15);
          y_im[l+sym_offset][i] = (((int32_t) (tmp_re*d_im[i+dt_offset] + tmp_im*d_re[i+dt_offset]))>>15);

          // cyclic shift
          ((int16_t *)&y_tilda_ptr[(l+sym_offset)*12+(i-(ncs_cell[ns][l]%12)+12)%12])[0] = y_re[l+sym_offset][i];
          ((int16_t *)&y_tilda_ptr[(l+sym_offset)*12+(i-(ncs_cell[ns][l]%12)+12)%12])[1] = y_im[l+sym_offset][i];

          // DMRS
          m_alpha_idx = (alpha_idx * i) % 12;
          if (l==1 || l==5) {
            ((int16_t *)&zptr[(l+sym_offset)*12+i])[0] =(((((int32_t) alphaTBL_re[m_alpha_idx]*ul_ref_sigs[u][v][0][i<<1] - (int32_t) alphaTBL_im[m_alpha_idx] * ul_ref_sigs[u][v][0][1+(i<<1)])>>15) * (int32_t)amp)>>15);
            ((int16_t *)&zptr[(l+sym_offset)*12+i])[1] =(((((int32_t) alphaTBL_re[m_alpha_idx]*ul_ref_sigs[u][v][0][1+(i<<1)] + (int32_t) alphaTBL_im[m_alpha_idx] * ul_ref_sigs[u][v][0][i<<1])>>15) * (int32_t)amp)>>15);
          }
        }

      } // l loop
    } // ns

    // DFT for pucch-data
    for (l=0; l<14; l++) {
      if (l==1 || l==5 || l==8 || l==12) {
        ;
      } else {
         pucchfmt3_Dft((int16_t*)&y_tilda_ptr[l*12],(int16_t*)&zptr[l*12]);
      }
    }


    // Mapping
    m = n3_pucch / N_PUCCH_SF0;

    if (shortened_format == 1) {
      nsymb = (N_UL_symb<<1) - 1;
    } else {
      nsymb = (N_UL_symb<<1);
   }

    for (j=0,l=0; l<(nsymb); l++) {

      if ((l<7) && ((m&1) == 0))
        re_offset = (m*6) + frame_parms->first_carrier_offset;
      else if ((l<7) && ((m&1) == 1))
        re_offset = frame_parms->first_carrier_offset + (frame_parms->N_RB_DL - (m>>1) - 1)*12;
      else if ((m&1) == 0)
        re_offset = frame_parms->first_carrier_offset + (frame_parms->N_RB_DL - (m>>1) - 1)*12;
      else
        re_offset = ((m-1)*6) + frame_parms->first_carrier_offset;

      if (re_offset > frame_parms->ofdm_symbol_size)
        re_offset -= (frame_parms->ofdm_symbol_size);

      symbol_offset = (unsigned int)frame_parms->ofdm_symbol_size*(l+(subframe*14));
      txptr = &txdataF[0][symbol_offset];

      for (i=0; i<12; i++,j++) {
          txptr[re_offset++] = z[j];

        if (re_offset==frame_parms->ofdm_symbol_size)
          re_offset = 0;

#ifdef DEBUG_PUCCH_TX
        msg("[PHY] PUCCH subframe %d (%d,%d,%d,%d) => %d,%d\n",subframe,l,i,re_offset-1,m,((int16_t *)&z[j])[0],((int16_t *)&z[j])[1]);
#endif
      }
    }

}

/* PUCCH format3 << */


//#define Amax 13
//void init_pucch2x_rx() {};


/* PUCCH format3 >> */
/* SubCarrier Demap */
uint16_t pucchfmt3_subCarrierDeMapping( PHY_VARS_eNB *eNB,
                                        int16_t SubCarrierDeMapData[NB_ANTENNAS_RX][14][12][2],
                                        uint16_t n3_pucch )
{
    LTE_eNB_COMMON *eNB_common_vars  = &eNB->common_vars;
    LTE_DL_FRAME_PARMS  *frame_parms = &eNB->frame_parms;
    int16_t             *rxptr;
    uint8_t             N_UL_symb    = D_NSYM1SLT;                      // only Normal CP format
    uint16_t            m;                                              // Mapping to physical resource blocks(m)
    uint32_t            aa;
    uint16_t            k, l;
    uint32_t            symbol_offset;
    uint16_t            carrier_offset;
    
    
    m = n3_pucch / D_NPUCCH_SF5;
    
    // Do detection
    for (aa=0; aa<frame_parms->nb_antennas_rx; aa++) {
        
        for (l=0; l<D_NSYM1SF; l++) {
            
            if ((l<N_UL_symb) && ((m&1) == 0))
                carrier_offset = (m*6) + frame_parms->first_carrier_offset;
            else if ((l<N_UL_symb) && ((m&1) == 1))
                carrier_offset = frame_parms->first_carrier_offset + (frame_parms->N_RB_DL - (m>>1) - 1)*12;
            else if ((m&1) == 0)
                carrier_offset = frame_parms->first_carrier_offset + (frame_parms->N_RB_DL - (m>>1) - 1)*12;
            else
                carrier_offset = (((m-1)*6) + frame_parms->first_carrier_offset);
            
            if (carrier_offset > frame_parms->ofdm_symbol_size)
                carrier_offset -= (frame_parms->ofdm_symbol_size);
            
            symbol_offset = (unsigned int)frame_parms->ofdm_symbol_size*l;
            rxptr = (int16_t *)&eNB_common_vars->rxdataF[0][aa][symbol_offset];
            
            for (k=0; k<12; k++,carrier_offset++) {
                SubCarrierDeMapData[aa][l][k][0] = (int16_t)rxptr[carrier_offset<<1];      // DeMapping Data I
                SubCarrierDeMapData[aa][l][k][1] = (int16_t)rxptr[1+(carrier_offset<<1)];  // DeMapping Date Q
                
                if (carrier_offset==frame_parms->ofdm_symbol_size)
                    carrier_offset = 0;
                
                #ifdef DEBUG_PUCCH_RX
                    LOG_D(PHY,"[eNB] PUCCH subframe %d (%d,%d,%d,%d) : (%d,%d)\n",subframe,l,k,carrier_offset,m,
                    SubCarrierDeMapData[aa][l][k][0],SubCarrierDeMapData[aa][l][k][1]);
                #endif
            }
        }
    }
    return 0;
}

/* cyclic shift hopping remove */
uint16_t pucchfmt3_Baseseq_csh_remove( int16_t SubCarrierDeMapData[NB_ANTENNAS_RX][14][12][2],
                                       int16_t CshData_fmt3[NB_ANTENNAS_RX][14][12][2],
                                       LTE_DL_FRAME_PARMS *frame_parms,
                                       uint8_t subframe,
                                       uint8_t ncs_cell[20][7] )
{
    //int16_t     calctmp_baSeq[2];
    int16_t     calctmp_beta[2];
    int16_t     calctmp_alphak[2];
    int16_t     calctmp_SCDeMapData_alphak[2];
    int32_t     n_cell_cs_div64;
    int32_t     n_cell_cs_modNSC_RB;
    
    //int32_t     NSlot1subframe  = D_NSLT1SF;
    int32_t     NSym1slot       = D_NSYM1SLT; // Symbol per 1slot
    int32_t     NSym1subframe   = D_NSYM1SF;  // Symbol per 1subframe
    int32_t     aa, symNo, slotNo, sym, k;
    
    
    for (aa=0; aa<frame_parms->nb_antennas_rx; aa++) {  // Antenna
        for (symNo=0; symNo<NSym1subframe; symNo++) {   // Symbol
            slotNo = symNo / NSym1slot;
            sym = symNo % NSym1slot;
            
            n_cell_cs_div64 = (int32_t)(ncs_cell[2*subframe+slotNo][sym]/64.0);
            n_cell_cs_modNSC_RB = ncs_cell[2*subframe+slotNo][sym] % 12;
            
            // for canceling e^(j*PI|_n_cs^cell(ns,l)/64_|/2).
            calctmp_beta[0] = RotTBL_re[(n_cell_cs_div64)&0x3];
            calctmp_beta[1] = RotTBL_im[(n_cell_cs_div64)&0x3];
            
            for (k=0; k<12; k++) {  // Sub Carrier
                
                // for canceling being cyclically shifted"(i+n_cs^cell(ns,l))".
                // e^((j*2PI(n_cs^cell(ns,l) mod N_SC)/N_SC)*k).
                calctmp_alphak[0] = alphaTBL_re[((n_cell_cs_modNSC_RB)*k)%12];
                calctmp_alphak[1] = alphaTBL_im[((n_cell_cs_modNSC_RB)*k)%12];
                
                // e^(-alphar*k)*r_l,m,n,k
                calctmp_SCDeMapData_alphak[0] = (((int32_t)SubCarrierDeMapData[aa][symNo][k][0] * calctmp_alphak[0] + (int32_t)SubCarrierDeMapData[aa][symNo][k][1] * calctmp_alphak[1])>>15);
                calctmp_SCDeMapData_alphak[1] = (((int32_t)SubCarrierDeMapData[aa][symNo][k][1] * calctmp_alphak[0] - (int32_t)SubCarrierDeMapData[aa][symNo][k][0] * calctmp_alphak[1])>>15);
                
                // (e^(-alphar*k)*r_l,m,n,k) * e^(-beta)
                CshData_fmt3[aa][symNo][k][0] = (((int32_t)calctmp_SCDeMapData_alphak[0] * calctmp_beta[0] + (int32_t)calctmp_SCDeMapData_alphak[1] * calctmp_beta[1])>>15);
                CshData_fmt3[aa][symNo][k][1] = (((int32_t)calctmp_SCDeMapData_alphak[1] * calctmp_beta[0] - (int32_t)calctmp_SCDeMapData_alphak[0] * calctmp_beta[1])>>15);
            }
        }
    }
    return 0;
}

#define MAXROW_TBL_SF5_OS_IDX    (5)    // Orthogonal sequence index
const int16_t TBL_3_SF5_GEN_N_DASH_NS[MAXROW_TBL_SF5_OS_IDX] = {0,3,6,8,10};

#define MAXROW_TBL_SF4_OS_IDX    (4)    // Orthogonal sequence index
const int16_t TBL_3_SF4_GEN_N_DASH_NS[MAXROW_TBL_SF4_OS_IDX] = {0,3,6,9};

/* Channel estimation */
uint16_t pucchfmt3_ChannelEstimation( int16_t SubCarrierDeMapData[NB_ANTENNAS_RX][14][12][2],
                                      double delta_theta[NB_ANTENNAS_RX][12],
                                      int16_t ChestValue[NB_ANTENNAS_RX][2][12][2],
                                      int16_t *Interpw,
                                      uint8_t subframe,
                                      uint8_t shortened_format,
                                      LTE_DL_FRAME_PARMS *frame_parms,
                                      uint16_t n3_pucch,
                                      uint16_t n3_pucch_array[NUMBER_OF_UE_MAX],
                                      uint8_t ncs_cell[20][7] )
{
    uint32_t        aa, symNo, k, slotNo, sym, i, j;
    int16_t         np, np_n, ip_ind;
    //int16_t         npucch_sf;
    int16_t         calctmp[2];
    int16_t         BsCshData[NB_ANTENNAS_RX][D_NSYM1SF][D_NSC1RB][2];
    //int16_t         delta_theta_calctmp[NB_ANTENNAS_RX][4][D_NSC1RB][2], delta_theta_comp[NB_ANTENNAS_RX][D_NSC1RB][2];
    int16_t         delta_theta_comp[NB_ANTENNAS_RX][D_NSC1RB][2];
    int16_t         CsData_allavg[NB_ANTENNAS_RX][14][2];
    int16_t         CsData_temp[NB_ANTENNAS_RX][D_NSYM1SF][D_NSC1RB][2];
    int32_t         IP_CsData_allsfavg[NB_ANTENNAS_RX][14][4][2];
    int32_t         IP_allavg[D_NPUCCH_SF5];
    //int16_t         temp_ch[2];
	int16_t         m[NUMBER_OF_UE_MAX], m_self, same_m_number;
	uint16_t        n3_pucch_sameRB[NUMBER_OF_UE_MAX];
	int16_t         n_oc0[NUMBER_OF_UE_MAX];
	int16_t         n_oc1[NUMBER_OF_UE_MAX];
	int16_t         np_n_array[2][NUMBER_OF_UE_MAX]; //Cyclic shift
	uint8_t N_PUCCH_SF0 = 5;
	uint8_t N_PUCCH_SF1 = (shortened_format==0)? 5:4;
    
    uint32_t u0 = (frame_parms->Nid_cell + frame_parms->pusch_config_common.ul_ReferenceSignalsPUSCH.grouphop[subframe<<1]) % 30;
    uint32_t u1 = (frame_parms->Nid_cell + frame_parms->pusch_config_common.ul_ReferenceSignalsPUSCH.grouphop[1+(subframe<<1)]) % 30;
    uint32_t v0=frame_parms->pusch_config_common.ul_ReferenceSignalsPUSCH.seqhop[subframe<<1];
    uint32_t v1=frame_parms->pusch_config_common.ul_ReferenceSignalsPUSCH.seqhop[1+(subframe<<1)];
    
    uint32_t u=u0;
    uint32_t v=v0;
    
    //double d_theta[32]={0.0};
    //int32_t temp_theta[32][2]={0};
    
    for (aa=0; aa<frame_parms->nb_antennas_rx; aa++) {
        for (symNo=0; symNo<D_NSYM1SF; symNo++){
            for(ip_ind=0; ip_ind<D_NPUCCH_SF5-1; ip_ind++) {
                IP_CsData_allsfavg[aa][symNo][ip_ind][0] = 0;
                IP_CsData_allsfavg[aa][symNo][ip_ind][1] = 0;
            }
        }
    }
	
	// compute m[], m_self
	for(i=0; i<NUMBER_OF_UE_MAX; i++) {
		m[i] = n3_pucch_array[i] / N_PUCCH_SF0; // N_PUCCH_SF0 = 5
		if(n3_pucch_array[i] == n3_pucch) {
			m_self = i;
		}
	}
	
	for(i=0; i<NUMBER_OF_UE_MAX; i++) {
		//printf("n3_pucch_array[%d]=%d, m[%d]=%d \n", i, n3_pucch_array[i], i, m[i]);
	}
	//printf("m_self=%d \n", m_self);
	
	// compute n3_pucch_sameRB[] // Not 4 not be equally divided
	for(i=0, same_m_number=0; i<NUMBER_OF_UE_MAX; i++) {
		if(m[i] == m[m_self]) {
			n3_pucch_sameRB[same_m_number] = n3_pucch_array[i];
			same_m_number++;
		}
	}
	//printf("same_m_number = %d \n", same_m_number);
	for(i=0; i<same_m_number; i++) {
		//printf("n3_pucch_sameRB[%d]=%d \n", i, n3_pucch_sameRB[i]);
	}
	
	// compute n_oc1[], n_oc0[]
	for(i=0; i<same_m_number; i++) {
		n_oc0[i] = n3_pucch_sameRB[i] % N_PUCCH_SF1; //N_PUCCH_SF1 = (shortened_format==0)? 5:4;
		if (N_PUCCH_SF1 == 5) {
			n_oc1[i] = (3 * n_oc0[i]) % N_PUCCH_SF1;
		} else {
			n_oc1[i] = n_oc0[i] % N_PUCCH_SF1;
		}
	}
	for(i=0; i<same_m_number; i++) {
		//printf("n_oc0[%d]=%d, n_oc1[%d]=%d \n", i, n_oc0[i], i, n_oc1[i]);
	}
	
	
	// np_n_array[][]
	for(i=0; i<same_m_number; i++) {
		if (N_PUCCH_SF1 == 5) {
			np_n_array[0][i] = TBL_3_SF5_GEN_N_DASH_NS[n_oc0[i]]; //slot0
			np_n_array[1][i] = TBL_3_SF5_GEN_N_DASH_NS[n_oc1[i]]; //slot1
		} else {
			np_n_array[0][i] = TBL_3_SF4_GEN_N_DASH_NS[n_oc0[i]];
			np_n_array[1][i] = TBL_3_SF4_GEN_N_DASH_NS[n_oc1[i]];
		}
	}
	for(i=0; i<same_m_number; i++) {
		//printf("np_n_array[0][%d]=%d ,np_n_array[1][%d]=%d \n", i, np_n_array[0][i], i, np_n_array[1][i]);
	}
    
    for (aa=0; aa<frame_parms->nb_antennas_rx; aa++) {
        for (symNo=0; symNo<D_NSYM1SF; symNo++){ // #define D_NSYM1SF       2*7
            slotNo = symNo / D_NSYM1SLT;
            sym = symNo % D_NSYM1SLT;
            
            for (k=0; k<D_NSC1RB; k++) { // #define D_NSC1RB        12
                
                // remove Base Sequence (c_r^*)*(r_l,m,m,n,k) = BsCshData
                BsCshData[aa][symNo][k][0] = (((int32_t)SubCarrierDeMapData[aa][symNo][k][0] * ul_ref_sigs[u][v][0][k<<1] + (int32_t)SubCarrierDeMapData[aa][symNo][k][1] * ul_ref_sigs[u][v][0][1+(k<<1)])>>15);
                BsCshData[aa][symNo][k][1] = (((int32_t)SubCarrierDeMapData[aa][symNo][k][1] * ul_ref_sigs[u][v][0][k<<1] - (int32_t)SubCarrierDeMapData[aa][symNo][k][0] * ul_ref_sigs[u][v][0][1+(k<<1)])>>15);
                
                if(shortened_format == 1) {
                    if (symNo < D_NSYM1SLT) { 
                        np = n3_pucch % D_NPUCCH_SF4;		// np = n_oc
                        np_n = TBL_3_SF4_GEN_N_DASH_NS[np]; //
                    } else {
                        np = n3_pucch % D_NPUCCH_SF4;		//
                        np_n = TBL_3_SF4_GEN_N_DASH_NS[np]; //
                    }
                    //npucch_sf = D_NPUCCH_SF4;// = 4
                } else {
                    if (symNo < D_NSYM1SLT) {
                        np = n3_pucch % D_NPUCCH_SF5;
                        np_n = TBL_3_SF5_GEN_N_DASH_NS[np];
                    } else {
                        np = (3 * n3_pucch) % D_NPUCCH_SF5;
                        np_n = TBL_3_SF5_GEN_N_DASH_NS[np];
                    }
                    //npucch_sf = D_NPUCCH_SF5;// = 5
                }
                // cyclic shift e^(-j * beta_n * k)
                calctmp[0] = alphaTBL_re[(((ncs_cell[2*subframe+slotNo][sym] + np_n)%D_NSC1RB)*k)%12];
                calctmp[1] = alphaTBL_im[(((ncs_cell[2*subframe+slotNo][sym] + np_n)%D_NSC1RB)*k)%12];
                
                // Channel Estimation 1A, g'(n_cs)_l,m,n
            	// CsData_temp = g_l,m,n,k
                // remove cyclic shift BsCshData * e^(-j * beta_n * k)
                CsData_temp[aa][symNo][k][0]=((((int32_t)BsCshData[aa][symNo][k][0] * calctmp[0] + (int32_t)BsCshData[aa][symNo][k][1] * calctmp[1])/ D_NSC1RB)>>15);
                CsData_temp[aa][symNo][k][1]=((((int32_t)BsCshData[aa][symNo][k][1] * calctmp[0] - (int32_t)BsCshData[aa][symNo][k][0] * calctmp[1])/ D_NSC1RB)>>15);
                
            	// Interference power for Channel Estimation 1A, No use Cyclic Shift g'(n_cs)_l,m,n
            	// Calculated by the cyclic shift that is not used  S(ncs)_est
            	ip_ind = 0;
	        	for(i=0; i<N_PUCCH_SF1; i++) {
					for(j=0; j<same_m_number; j++) {	//np_n_array Loop
						if(shortened_format == 1) {
							if(symNo < D_NSYM1SLT) { // if SF==1 slot0
								if(TBL_3_SF4_GEN_N_DASH_NS[i] == np_n_array[0][j]) {
									break;
								}
            				} else { // if SF==1 slot1
								if(TBL_3_SF4_GEN_N_DASH_NS[i] == np_n_array[1][j]) {
									break;
								}
            				}
						} else {
							if(symNo < D_NSYM1SLT) { // if SF==0 slot0
								if(TBL_3_SF5_GEN_N_DASH_NS[i] == np_n_array[0][j]) {
									break;
								}
            				} else { // if SF==0 slot1
								if(TBL_3_SF5_GEN_N_DASH_NS[i] == np_n_array[1][j]) {
									break;
								}
            				}
						}
						if(j == same_m_number - 1) { //when even once it has not been used
							if(shortened_format == 1) {
								calctmp[0] = alphaTBL_re[(((ncs_cell[2*subframe+slotNo][sym] + TBL_3_SF4_GEN_N_DASH_NS[i])%D_NSC1RB)*k)%12]; //D_NSC1RB =12
		                        calctmp[1] = alphaTBL_im[(((ncs_cell[2*subframe+slotNo][sym] + TBL_3_SF4_GEN_N_DASH_NS[i])%D_NSC1RB)*k)%12];
							} else {
								calctmp[0] = alphaTBL_re[(((ncs_cell[2*subframe+slotNo][sym] + TBL_3_SF5_GEN_N_DASH_NS[i])%D_NSC1RB)*k)%12];
		                        calctmp[1] = alphaTBL_im[(((ncs_cell[2*subframe+slotNo][sym] + TBL_3_SF5_GEN_N_DASH_NS[i])%D_NSC1RB)*k)%12];
							}
							// IP_CsData_allsfavg = g'(n_cs)_l,m,n
	                        IP_CsData_allsfavg[aa][symNo][ip_ind][0] += ((((int32_t)BsCshData[aa][symNo][k][0] * calctmp[0] + (int32_t)BsCshData[aa][symNo][k][1] * calctmp[1]))>>15);
	                        IP_CsData_allsfavg[aa][symNo][ip_ind][1] += ((((int32_t)BsCshData[aa][symNo][k][1] * calctmp[0] - (int32_t)BsCshData[aa][symNo][k][0] * calctmp[1]))>>15);
							if((symNo == 1 || symNo == 5 || symNo == 8 || symNo == 12)) {
							}
	                        ip_ind++;
		        		}
					}
	        	}
            }
            if(symNo > D_NSYM1SLT-1) {
                u=u1;
                v=v1;
            }
        }
    }
    
    for (aa=0; aa<frame_parms->nb_antennas_rx; aa++) {
        for (symNo=0; symNo<D_NSYM1SF; symNo++){
            CsData_allavg[aa][symNo][0] = 0;
            CsData_allavg[aa][symNo][1] = 0;
            for (k=0; k<D_NSC1RB; k++) {
              CsData_allavg[aa][symNo][0] += (int16_t)((double)CsData_temp[aa][symNo][k][0]);
              CsData_allavg[aa][symNo][1] += (int16_t)((double)CsData_temp[aa][symNo][k][1]);
            }
        }
    }
    
    // Frequency deviation estimation
    for (aa=0; aa<frame_parms->nb_antennas_rx; aa++) {
        for (k=0; k<12; k++) {
            delta_theta_comp[aa][k][0] = 0;
            delta_theta_comp[aa][k][1] = 0;
            
            delta_theta_comp[aa][k][0] += (((int32_t)CsData_temp[aa][1][k][0] * CsData_temp[aa][5][k][0] + (int32_t)((CsData_temp[aa][1][k][1])*CsData_temp[aa][5][k][1]))>>8);
            delta_theta_comp[aa][k][1] += (((int32_t)CsData_temp[aa][1][k][0]*CsData_temp[aa][5][k][1] - (int32_t)((CsData_temp[aa][1][k][1])*CsData_temp[aa][5][k][0]) )>>8);
            
            delta_theta_comp[aa][k][0] += (((int32_t)CsData_temp[aa][8][k][0] * CsData_temp[aa][12][k][0] + (int32_t)((CsData_temp[aa][8][k][1])*CsData_temp[aa][12][k][1]))>>8);
            delta_theta_comp[aa][k][1] += (((int32_t)CsData_temp[aa][8][k][0]*CsData_temp[aa][12][k][1] - (int32_t)((CsData_temp[aa][8][k][1])*CsData_temp[aa][12][k][0]))>>8);
            
            delta_theta[aa][k] = atan2((double)delta_theta_comp[aa][k][1], (double)delta_theta_comp[aa][k][0]) / 4.0;
        }
    }
    
    for (aa=0; aa<frame_parms->nb_antennas_rx; aa++) {
        for (k=0; k<D_NSC1RB; k++) {
            ChestValue[aa][0][k][0] = (int16_t)((CsData_allavg[aa][1][0] + (int16_t)(((double)CsData_allavg[aa][5][0] * cos(delta_theta[aa][k]*4)) + ((double)CsData_allavg[aa][5][1] * sin(delta_theta[aa][k]*4)))) /(2*D_NSC1RB)) ;
            ChestValue[aa][0][k][1] = (int16_t)((CsData_allavg[aa][1][1] + (int16_t)(((double)CsData_allavg[aa][5][1] * cos(delta_theta[aa][k]*4)) - ((double)CsData_allavg[aa][5][0] * sin(delta_theta[aa][k]*4)))) /(2*D_NSC1RB)) ;
            ChestValue[aa][1][k][0] = (int16_t)((CsData_allavg[aa][8][0] + (int16_t)(((double)CsData_allavg[aa][12][0] * cos(delta_theta[aa][k]*4)) + ((double)CsData_allavg[aa][12][1] * sin(delta_theta[aa][k]*4)))) /(2*D_NSC1RB)) ;
            ChestValue[aa][1][k][1] = (int16_t)((CsData_allavg[aa][8][1] + (int16_t)(((double)CsData_allavg[aa][12][1] * cos(delta_theta[aa][k]*4)) - ((double)CsData_allavg[aa][12][0] * sin(delta_theta[aa][k]*4)))) /(2*D_NSC1RB)) ;
        }
    }
    
    *Interpw = 0;
    for (aa=0; aa<frame_parms->nb_antennas_rx; aa++) {
    	if(ip_ind == 0) {//ip_ind= The total number of cyclic shift of non-use
    		*Interpw = 1;
    		break;
    	}
        for(i=0; i<ip_ind; i++) {
            IP_allavg[i] = 0;
            
            IP_allavg[i] += (((int32_t)IP_CsData_allsfavg[aa][1][i][0] * IP_CsData_allsfavg[aa][1][i][0] + (int32_t)IP_CsData_allsfavg[aa][1][i][1]*IP_CsData_allsfavg[aa][1][i][1])>>8);
        	IP_allavg[i] += (((int32_t)IP_CsData_allsfavg[aa][5][i][0] * IP_CsData_allsfavg[aa][5][i][0] + (int32_t)IP_CsData_allsfavg[aa][5][i][1]*IP_CsData_allsfavg[aa][5][i][1])>>8);
            IP_allavg[i] += (((int32_t)IP_CsData_allsfavg[aa][8][i][0] * IP_CsData_allsfavg[aa][8][i][0] + (int32_t)IP_CsData_allsfavg[aa][8][i][1]*IP_CsData_allsfavg[aa][8][i][1])>>8);
            IP_allavg[i] += (((int32_t)IP_CsData_allsfavg[aa][12][i][0] * IP_CsData_allsfavg[aa][12][i][0] + (int32_t)IP_CsData_allsfavg[aa][12][i][1]*IP_CsData_allsfavg[aa][12][i][1])>>8);
        	*Interpw += IP_allavg[i]/(2*D_NSLT1SF*frame_parms->nb_antennas_rx*ip_ind*12);
        }
    }
    return 0;
}

/* Channel Equalization */
uint16_t pucchfmt3_Equalization( int16_t CshData_fmt3[NB_ANTENNAS_RX][14][12][2],
                                 int16_t ChdetAfterValue_fmt3[NB_ANTENNAS_RX][14][12][2],
                                 int16_t ChestValue[NB_ANTENNAS_RX][2][12][2],
                                 LTE_DL_FRAME_PARMS *frame_parms)
{
    int16_t aa, sltNo, symNo, k;
    
    for (aa=0; aa<frame_parms->nb_antennas_rx; aa++) {
        sltNo = 0;
        for (symNo=0; symNo<D_NSYM1SF; symNo++){
            if(symNo >= D_NSYM1SLT) {
                sltNo = 1;
            }
            for (k=0; k<D_NSC1RB; k++){
                ChdetAfterValue_fmt3[aa][symNo][k][0] = (((int32_t)CshData_fmt3[aa][symNo][k][0] * ChestValue[aa][sltNo][k][0] + (int32_t)CshData_fmt3[aa][symNo][k][1] * ChestValue[aa][sltNo][k][1])>>8);
                ChdetAfterValue_fmt3[aa][symNo][k][1] = (((int32_t)CshData_fmt3[aa][symNo][k][1] * ChestValue[aa][sltNo][k][0] - (int32_t)CshData_fmt3[aa][symNo][k][0] * ChestValue[aa][sltNo][k][1])>>8);
            }
        }
    }
    return 0;
}

/* Frequency deviation remove AFC */
uint16_t pucchfmt3_FrqDevRemove( int16_t ChdetAfterValue_fmt3[NB_ANTENNAS_RX][14][12][2],
                             double delta_theta[NB_ANTENNAS_RX][12],
                             int16_t RemoveFrqDev_fmt3[NB_ANTENNAS_RX][2][5][12][2],
                             LTE_DL_FRAME_PARMS *frame_parms )
{
    int16_t aa, sltNo, symNo1slt, k, n;
    double calctmp[2];
    
    for (aa=0; aa<frame_parms->nb_antennas_rx; aa++) {
        for(sltNo = 0; sltNo<D_NSLT1SF; sltNo++)
        {
            n=0;
            for (symNo1slt=0, n=0; symNo1slt<D_NSYM1SLT; symNo1slt++){
                if(!((symNo1slt==1) || (symNo1slt==5))) {
                    for (k=0; k<D_NSC1RB; k++) {
                        calctmp[0] = cos(delta_theta[aa][k] * (n-1));
                        calctmp[1] = sin(delta_theta[aa][k] * (n-1));
                        
                        RemoveFrqDev_fmt3[aa][sltNo][n][k][0] = (int16_t)((double)ChdetAfterValue_fmt3[aa][(sltNo*D_NSYM1SLT)+symNo1slt][k][0] * calctmp[0] 
                                                                + (double)ChdetAfterValue_fmt3[aa][(sltNo*D_NSYM1SLT)+symNo1slt][k][1] * calctmp[1]);
                        RemoveFrqDev_fmt3[aa][sltNo][n][k][1] = (int16_t)((double)ChdetAfterValue_fmt3[aa][(sltNo*D_NSYM1SLT)+symNo1slt][k][1] * calctmp[0] 
                                                                - (double)ChdetAfterValue_fmt3[aa][(sltNo*D_NSYM1SLT)+symNo1slt][k][0] * calctmp[1]);
                    }
                    n++;
                }
            }
        }
    }
    return 0;
}

//for opt.Lev.2 
#define  MAXROW_TBL_SF5  5
#define  MAXCLM_TBL_SF5  5
const int16_t TBL_3_SF5[MAXROW_TBL_SF5][MAXCLM_TBL_SF5][2] = 
                         {{ {32767,0}, {32767,0}, {32767,0}, {32767,0}, {32767,0}},
                          { {32767,0}, {10126, 31163}, {-26509, 19260}, {-26509, -19260}, {10126, -31163}},
                          { {32767,0}, {-26509, 19260}, {10126, -31163}, {10126, 31163}, {-26509, -19260}},
                          { {32767,0}, {-26509, -19260}, {10126, 31163}, {10126, -31163}, {-26509, 19260}},
                          { {32767,0}, {10126, -31163}, {-26509, -19260}, {-26509, 19260}, {10126, 31163}}};

#define  MAXROW_TBL_SF4_fmt3 4
#define  MAXCLM_TBL_SF4      4
const int16_t TBL_3_SF4[MAXROW_TBL_SF4_fmt3][MAXCLM_TBL_SF4][2] = 
                         {{ {32767,0}, {32767,0}, {32767,0}, {32767,0}},
                          { {32767,0}, {-32767,0}, {32767,0}, {-32767,0}},
                          { {32767,0}, {32767,0}, {-32767,0}, {-32767,0}},
                          { {32767,0}, {-32767,0}, {-32767,0}, {32767,0}}};

/* orthogonal sequence remove */
uint16_t pucchfmt3_OrthSeqRemove( int16_t RemoveFrqDev_fmt3[NB_ANTENNAS_RX][2][5][12][2],
                                  int16_t Fmt3xDataRmvOrth[NB_ANTENNAS_RX][2][5][12][2],
                                  uint8_t shortened_format,
                                  uint16_t n3_pucch,
                                  LTE_DL_FRAME_PARMS *frame_parms )
{
    int16_t aa, sltNo, n, k;
    int16_t Npucch_sf;
    int16_t noc;
    
    for (aa=0; aa<frame_parms->nb_antennas_rx; aa++) {
        for (sltNo=0; sltNo<D_NSLT1SF; sltNo++){
            if(shortened_format == 1) {
                if(sltNo == 0) {
                    noc = n3_pucch % D_NPUCCH_SF4;
                    Npucch_sf = D_NPUCCH_SF5;
                } else {
                    noc = n3_pucch % D_NPUCCH_SF4;
                    Npucch_sf = D_NPUCCH_SF4;
                }
            } else {
                if(sltNo == 0) {
                    noc = n3_pucch % D_NPUCCH_SF5;
                    Npucch_sf = D_NPUCCH_SF5;
                } else {
                    noc = (3 * n3_pucch) % D_NPUCCH_SF5;
                    Npucch_sf = D_NPUCCH_SF5;
                }
            }
            for (n=0; n<Npucch_sf; n++){
                for (k=0; k<D_NSC1RB; k++) {
                    if ((sltNo == 1) && (shortened_format == 1)) {
                      Fmt3xDataRmvOrth[aa][sltNo][n][k][0] = (((int32_t)RemoveFrqDev_fmt3[aa][sltNo][n][k][0] * TBL_3_SF4[noc][n][0] + (int32_t)RemoveFrqDev_fmt3[aa][sltNo][n][k][1] * TBL_3_SF4[noc][n][1])>>15);
                      Fmt3xDataRmvOrth[aa][sltNo][n][k][1] = (((int32_t)RemoveFrqDev_fmt3[aa][sltNo][n][k][1] * TBL_3_SF4[noc][n][0] - (int32_t)RemoveFrqDev_fmt3[aa][sltNo][n][k][0] * TBL_3_SF4[noc][n][1])>>15);
                    } else {
                      Fmt3xDataRmvOrth[aa][sltNo][n][k][0] = (((int32_t)RemoveFrqDev_fmt3[aa][sltNo][n][k][0] * TBL_3_SF5[noc][n][0] + (int32_t)RemoveFrqDev_fmt3[aa][sltNo][n][k][1] * TBL_3_SF5[noc][n][1])>>15);
                      Fmt3xDataRmvOrth[aa][sltNo][n][k][1] = (((int32_t)RemoveFrqDev_fmt3[aa][sltNo][n][k][1] * TBL_3_SF5[noc][n][0] - (int32_t)RemoveFrqDev_fmt3[aa][sltNo][n][k][0] * TBL_3_SF5[noc][n][1])>>15);
                    }
                }
            }
        }
    }
    return 0;
}

/* averaging antenna */
uint16_t pucchfmt3_AvgAnt( int16_t Fmt3xDataRmvOrth[NB_ANTENNAS_RX][2][5][12][2],
                           int16_t Fmt3xDataAvgAnt[2][5][12][2],
                           uint8_t shortened_format,
                           LTE_DL_FRAME_PARMS *frame_parms )
{
    int16_t aa, sltNo, n, k;
    int16_t Npucch_sf;
    
    for (sltNo=0; sltNo<D_NSLT1SF; sltNo++){
        if((sltNo == 1) && (shortened_format == 1)) {
            Npucch_sf = D_NPUCCH_SF4;
        } else {
            Npucch_sf = D_NPUCCH_SF5;
        }
        for (n=0; n<Npucch_sf; n++){
            for (k=0; k<D_NSC1RB; k++) {
                Fmt3xDataAvgAnt[sltNo][n][k][0] = 0;
                Fmt3xDataAvgAnt[sltNo][n][k][1] = 0;
                for (aa=0; aa<frame_parms->nb_antennas_rx; aa++) {
                    Fmt3xDataAvgAnt[sltNo][n][k][0] += Fmt3xDataRmvOrth[aa][sltNo][n][k][0]  / frame_parms->nb_antennas_rx;
                    Fmt3xDataAvgAnt[sltNo][n][k][1] += Fmt3xDataRmvOrth[aa][sltNo][n][k][1]  / frame_parms->nb_antennas_rx;
                }
            }
        }
    }
    return 0;
}

/* averaging symbol */
uint16_t pucchfmt3_AvgSym( int16_t Fmt3xDataAvgAnt[2][5][12][2],
                           int16_t Fmt3xDataAvgSym[2][12][2],
                           uint8_t shortened_format )
{
    int16_t sltNo, n, k;
    int16_t Npucch_sf;
    
    for (sltNo=0; sltNo<D_NSLT1SF; sltNo++){
        if((sltNo == 1) && (shortened_format == 1)) {
            Npucch_sf = D_NPUCCH_SF4;
        } else {
            Npucch_sf = D_NPUCCH_SF5;
        }
        for (k=0; k<D_NSC1RB; k++) {
            Fmt3xDataAvgSym[sltNo][k][0] = 0;
            Fmt3xDataAvgSym[sltNo][k][1] = 0;
            for (n=0; n<Npucch_sf; n++){
                Fmt3xDataAvgSym[sltNo][k][0] += Fmt3xDataAvgAnt[sltNo][n][k][0] / Npucch_sf;
                Fmt3xDataAvgSym[sltNo][k][1] += Fmt3xDataAvgAnt[sltNo][n][k][1] / Npucch_sf;
            }
        }
    }
    return 0;
}

/* iDFT */
void pucchfmt3_IDft2( int16_t *x, int16_t *y )
{
  int16_t i, k;
  int16_t tmp[2];
  int16_t calctmp[D_NSC1RB*2]={0};
  
  for(k=0; k<D_NSC1RB; k++) {
    for (i=0; i<D_NSC1RB; i++) {
      tmp[0] = alphaTBL_re[((i*k)%12)];
      tmp[1] = alphaTBL_im[((i*k)%12)];
      
      calctmp[2*k] += (((int32_t)x[2*i] * tmp[0] - (int32_t)x[2*i+1] * tmp[1])>>15);
      calctmp[2*k+1] += (((int32_t)x[2*i+1] * tmp[0] + (int32_t)x[2*i] * tmp[1])>>15);
    }
    y[2*k] = (int16_t)( (double) calctmp[2*k] / sqrt(D_NSC1RB));
    y[2*k+1] = (int16_t)((double) calctmp[2*k+1] / sqrt(D_NSC1RB));
  }
}

/* descramble */
uint16_t pucchfmt3_Descramble( int16_t IFFTOutData_Fmt3[2][12][2],
                               int16_t b[48],
                               uint8_t subframe,
                               uint32_t Nid_cell,
                               uint32_t rnti
                              )
{
    int16_t m, k, c,i,j;
    uint32_t cinit = 0;
    uint32_t x1;
    uint32_t s,s0,s1;
    cinit = (subframe + 1) * ((2 * Nid_cell + 1)<<16) + rnti;
    s0 = lte_gold_generic(&x1,&cinit,1);
    s1 = lte_gold_generic(&x1,&cinit,0);
    i=0;
    for (m=0; m<D_NSLT1SF; m++){
        for(k=0; k<D_NSC1RB; k++) {
            s = (i<32)? s0:s1;
            j = (i<32)? i:(i-32);
            c=((s>>j)&1);
            b[i] = (IFFTOutData_Fmt3[m][k][0] * (1 - 2*c));
            i++;
          
            s = (i<32)? s0:s1;
            j = (i<32)? i:(i-32);
            c=((s>>j)&1);
            b[i] = (IFFTOutData_Fmt3[m][k][1] * (1 - 2*c));
            i++;
        }
    }
    return 0;
}

int16_t pucchfmt3_Decode( int16_t b[48],
                          uint8_t subframe,
                          int16_t DTXthreshold,
                          int16_t Interpw,
                          uint8_t do_sr)
{
    int16_t c, i;
    int32_t Rho_tmp;
    int16_t c_max;
    int32_t Rho_max;
    int16_t bit_pattern;
    
    /* Is payload 6bit or 7bit? */
    if( do_sr == 1 ) {
        bit_pattern = 128;
    } else {
        bit_pattern = 64;
    }
    
    c=0;
    Rho_tmp = 0;
    for (i=0;i<48;i++) {
        Rho_tmp += b[i] * (1-2*chcod_tbl[c][i]);
    }
    c_max = c;
    Rho_max = Rho_tmp;
    
    for(c=1; c<bit_pattern; c++) {
        Rho_tmp = 0;
        for (i=0;i<48;i++) {
            Rho_tmp += b[i] * (1-2*chcod_tbl[c][i]);
        }
        if (Rho_tmp > Rho_max) {
            c_max = c;
            Rho_max = Rho_tmp;
        }
    }
    if(Interpw<1){
      Interpw=1;
    }
    if((Rho_max/Interpw) > DTXthreshold) {
        // ***Log
        return c_max;
    } else {
        // ***Log
        return -1;
    }
}

/* PUCCH format3 << */

uint32_t rx_pucch(PHY_VARS_eNB *eNB,
		  PUCCH_FMT_t fmt,
		  uint8_t UE_id,
		  uint16_t n1_pucch,
		  uint16_t n2_pucch,
		  uint8_t shortened_format,
		  uint8_t *payload,
		  int     frame,
		  uint8_t subframe,
		  uint8_t pucch1_thres)
{


  static int first_call=1;
  LTE_eNB_COMMON *common_vars                = &eNB->common_vars;
  LTE_DL_FRAME_PARMS *frame_parms                    = &eNB->frame_parms;
  //  PUCCH_CONFIG_DEDICATED *pucch_config_dedicated = &eNB->pucch_config_dedicated[UE_id];
  int8_t sigma2_dB                                   = eNB->measurements[0].n0_subband_power_tot_dB[0]-10;
  uint32_t *Po_PUCCH                                  = &(eNB->UE_stats[UE_id].Po_PUCCH);
  int32_t *Po_PUCCH_dBm                              = &(eNB->UE_stats[UE_id].Po_PUCCH_dBm);
  uint32_t *Po_PUCCH1_below                           = &(eNB->UE_stats[UE_id].Po_PUCCH1_below);
  uint32_t *Po_PUCCH1_above                           = &(eNB->UE_stats[UE_id].Po_PUCCH1_above);
  int32_t *Po_PUCCH_update                           = &(eNB->UE_stats[UE_id].Po_PUCCH_update);
  uint32_t u,v,n,aa;
  uint32_t z[12*14];
  int16_t *zptr;
  int16_t rxcomp[NB_ANTENNAS_RX][2*12*14];
  uint8_t ns,N_UL_symb,nsymb,n_oc,n_oc0,n_oc1;
  uint8_t c = (frame_parms->Ncp==0) ? 3 : 2;
  uint16_t nprime,nprime0,nprime1;
  uint16_t i,j,re_offset,thres,h,off;
  uint8_t Nprime_div_deltaPUCCH_Shift,Nprime,d;
  uint8_t m,l,refs,phase,re,l2,phase_max=0;
  uint8_t n_cs,S,alpha_ind,rem;
  int16_t tmp_re,tmp_im,W_re=0,W_im=0;
  int16_t *rxptr;
  uint32_t symbol_offset;
  int16_t stat_ref_re,stat_ref_im,*cfo,chest_re,chest_im;
  int32_t stat_re=0,stat_im=0;
  uint32_t stat,stat_max=0;

  uint8_t deltaPUCCH_Shift          = frame_parms->pucch_config_common.deltaPUCCH_Shift;
  uint8_t NRB2                      = frame_parms->pucch_config_common.nRB_CQI;
  uint8_t Ncs1_div_deltaPUCCH_Shift = frame_parms->pucch_config_common.nCS_AN;

  uint32_t u0 = (frame_parms->Nid_cell + frame_parms->pusch_config_common.ul_ReferenceSignalsPUSCH.grouphop[subframe<<1]) % 30;
  uint32_t u1 = (frame_parms->Nid_cell + frame_parms->pusch_config_common.ul_ReferenceSignalsPUSCH.grouphop[1+(subframe<<1)]) % 30;
  uint32_t v0=frame_parms->pusch_config_common.ul_ReferenceSignalsPUSCH.seqhop[subframe<<1];
  uint32_t v1=frame_parms->pusch_config_common.ul_ReferenceSignalsPUSCH.seqhop[1+(subframe<<1)];
  int chL;

  /* PUCCH format3 >> */
  uint16_t Ret = 0;
  int16_t SubCarrierDeMapData[NB_ANTENNAS_RX][14][12][2];       //[Antenna][Symbol][Subcarrier][Complex]
  int16_t CshData_fmt3[NB_ANTENNAS_RX][14][12][2];              //[Antenna][Symbol][Subcarrier][Complex]
  double delta_theta[NB_ANTENNAS_RX][12];                      //[Antenna][Subcarrier][Complex]
  int16_t ChestValue[NB_ANTENNAS_RX][2][12][2];                 //[Antenna][Slot][Subcarrier][Complex]
  int16_t ChdetAfterValue_fmt3[NB_ANTENNAS_RX][14][12][2];      //[Antenna][Symbol][Subcarrier][Complex]
  int16_t RemoveFrqDev_fmt3[NB_ANTENNAS_RX][2][5][12][2];       //[Antenna][Slot][PUCCH_Symbol][Subcarrier][Complex]
  int16_t Fmt3xDataRmvOrth[NB_ANTENNAS_RX][2][5][12][2];        //[Antenna][Slot][PUCCH_Symbol][Subcarrier][Complex]
  int16_t Fmt3xDataAvgAnt[2][5][12][2];                         //[Slot][PUCCH_Symbol][Subcarrier][Complex]
  int16_t Fmt3xDataAvgSym[2][12][2];                            //[Slot][Subcarrier][Complex]
  int16_t IFFTOutData_Fmt3[2][12][2];                           //[Slot][Subcarrier][Complex]
  int16_t b[48];                                                //[bit]
  //int16_t IP_CsData_allavg[NB_ANTENNAS_RX][12][4][2];           //[Antenna][Symbol][Nouse Cyclic Shift][Complex]
  int16_t payload_entity = -1;
  int16_t Interpw;
  int16_t payload_max;
  
  // TODO
  // When using PUCCH format3, it must be an argument of rx_pucch function
  uint16_t n3_pucch = 20;
  uint16_t n3_pucch_array[NUMBER_OF_UE_MAX]={1};
  n3_pucch_array[0]=n3_pucch;
  uint8_t do_sr = 1;
  uint16_t crnti=0x1234;
  int16_t DTXthreshold = 10;
  /* PUCCH format3 << */

  if (first_call == 1) {
    for (i=0;i<10;i++) {
      for (j=0;j<NUMBER_OF_UE_MAX;j++) {
	eNB->pucch1_stats_cnt[j][i]=0;
	eNB->pucch1ab_stats_cnt[j][i]=0;
      }
    }
    first_call=0;
  }
  /*
  switch (frame_parms->N_RB_UL) {

  case 6:
    sigma2_dB -= 8;
    break;
  case 25:
    sigma2_dB -= 14;
    break;
  case 50:
    sigma2_dB -= 17;
    break;
  case 100:
    sigma2_dB -= 20;
    break;
  default:
    sigma2_dB -= 14;
  }
  */  

  if(fmt!=pucch_format3) {  /* PUCCH format3 */
  
  // TODO
  // "SR+ACK/NACK" length is only 7 bits.
  // This restriction will be lifted in the future.
  // "CQI/PMI/RI+ACK/NACK" will be supported in the future.

  if ((deltaPUCCH_Shift==0) || (deltaPUCCH_Shift>3)) {
    LOG_E(PHY,"[eNB] rx_pucch: Illegal deltaPUCCH_shift %d (should be 1,2,3)\n",deltaPUCCH_Shift);
    return(-1);
  }

  if (Ncs1_div_deltaPUCCH_Shift > 7) {
    LOG_E(PHY,"[eNB] rx_pucch: Illegal Ncs1_div_deltaPUCCH_Shift %d (should be 0...7)\n",Ncs1_div_deltaPUCCH_Shift);
    return(-1);
  }

  zptr = (int16_t *)z;
  thres = (c*Ncs1_div_deltaPUCCH_Shift);
  Nprime_div_deltaPUCCH_Shift = (n1_pucch < thres) ? Ncs1_div_deltaPUCCH_Shift : (12/deltaPUCCH_Shift);
  Nprime = Nprime_div_deltaPUCCH_Shift * deltaPUCCH_Shift;

#ifdef DEBUG_PUCCH_RX
  printf("[eNB] PUCCH: cNcs1/deltaPUCCH_Shift %d, Nprime %d, n1_pucch %d\n",thres,Nprime,n1_pucch);
#endif

  N_UL_symb = (frame_parms->Ncp==NORMAL) ? 7 : 6;

  if (n1_pucch < thres)
    nprime0=n1_pucch;
  else
    nprime0 = (n1_pucch - thres)%(12*c/deltaPUCCH_Shift);

  if (n1_pucch >= thres)
    nprime1= ((c*(nprime0+1))%((12*c/deltaPUCCH_Shift)+1))-1;
  else {
    d = (frame_parms->Ncp==0) ? 2 : 0;
    h= (nprime0+d)%(c*Nprime_div_deltaPUCCH_Shift);
    nprime1 = (h/c) + (h%c)*Nprime_div_deltaPUCCH_Shift;
  }

#ifdef DEBUG_PUCCH_RX
  printf("PUCCH: nprime0 %d nprime1 %d\n",nprime0,nprime1);
#endif

  n_oc0 = nprime0/Nprime_div_deltaPUCCH_Shift;

  if (frame_parms->Ncp==1)
    n_oc0<<=1;

  n_oc1 = nprime1/Nprime_div_deltaPUCCH_Shift;

  if (frame_parms->Ncp==1)  // extended CP
    n_oc1<<=1;

#ifdef DEBUG_PUCCH_RX
  printf("[eNB] PUCCH: noc0 %d noc11 %d\n",n_oc0,n_oc1);
#endif

  nprime=nprime0;
  n_oc  =n_oc0;

  // loop over 2 slots
  for (ns=(subframe<<1),u=u0,v=v0; ns<(2+(subframe<<1)); ns++,u=u1,v=v1) {

    if ((nprime&1) == 0)
      S=0;  // 1
    else
      S=1;  // j
    /*
    if (fmt==pucch_format1)
      LOG_I(PHY,"[eNB] subframe %d => PUCCH1: u%d %d, v%d %d : ", subframe,ns&1,u,ns&1,v);
    else
      LOG_I(PHY,"[eNB] subframe %d => PUCCH1a/b: u%d %d, v%d %d : ", subframe,ns&1,u,ns&1,v);
    */

    //loop over symbols in slot
    for (l=0; l<N_UL_symb; l++) {
      // Compute n_cs (36.211 p. 18)
      n_cs = eNB->ncs_cell[ns][l];

      if (frame_parms->Ncp==0) { // normal CP
        n_cs = ((uint16_t)n_cs + (nprime*deltaPUCCH_Shift + (n_oc%deltaPUCCH_Shift))%Nprime)%12;
      } else {
        n_cs = ((uint16_t)n_cs + (nprime*deltaPUCCH_Shift + (n_oc>>1))%Nprime)%12;
      }



      refs=0;

      // Comput W_noc(m) (36.211 p. 19)
      if ((ns==(1+(subframe<<1))) && (shortened_format==1)) {  // second slot and shortened format

        if (l<2) {                                         // data
          W_re=W3_re[n_oc][l];
          W_im=W3_im[n_oc][l];
        } else if ((l<N_UL_symb-2)&&(frame_parms->Ncp==0)) { // reference and normal CP
          W_re=W3_re[n_oc][l-2];
          W_im=W3_im[n_oc][l-2];
          refs=1;
        } else if ((l<N_UL_symb-2)&&(frame_parms->Ncp==1)) { // reference and extended CP
          W_re=W4[n_oc][l-2];
          W_im=0;
          refs=1;
        } else if ((l>=N_UL_symb-2)) {                      // data
          W_re=W3_re[n_oc][l-N_UL_symb+4];
          W_im=W3_im[n_oc][l-N_UL_symb+4];
        }
      } else {
        if (l<2) {                                         // data
          W_re=W4[n_oc][l];
          W_im=0;
        } else if ((l<N_UL_symb-2)&&(frame_parms->Ncp==NORMAL)) { // reference and normal CP
          W_re=W3_re[n_oc][l-2];
          W_im=W3_im[n_oc][l-2];
          refs=1;
        } else if ((l<N_UL_symb-2)&&(frame_parms->Ncp==EXTENDED)) { // reference and extended CP
          W_re=W4[n_oc][l-2];
          W_im=0;
          refs=1;
        } else if ((l>=N_UL_symb-2)) {                     // data
          W_re=W4[n_oc][l-N_UL_symb+4];
          W_im=0;
        }
      }

      // multiply W by S(ns) (36.211 p.17). only for data, reference symbols do not have this factor
      if ((S==1)&&(refs==0)) {
        tmp_re = W_re;
        W_re = -W_im;
        W_im = tmp_re;
      }

#ifdef DEBUG_PUCCH_RX
      printf("[eNB] PUCCH: ncs[%d][%d]=%d, W_re %d, W_im %d, S %d, refs %d\n",ns,l,n_cs,W_re,W_im,S,refs);
#endif
      alpha_ind=0;
      // compute output sequence

      for (n=0; n<12; n++) {

        // this is r_uv^alpha(n)
        tmp_re = (int16_t)(((int32_t)alpha_re[alpha_ind] * ul_ref_sigs[u][v][0][n<<1] - (int32_t)alpha_im[alpha_ind] * ul_ref_sigs[u][v][0][1+(n<<1)])>>15);
        tmp_im = (int16_t)(((int32_t)alpha_re[alpha_ind] * ul_ref_sigs[u][v][0][1+(n<<1)] + (int32_t)alpha_im[alpha_ind] * ul_ref_sigs[u][v][0][n<<1])>>15);

        // this is S(ns)*w_noc(m)*r_uv^alpha(n)
        zptr[n<<1] = (tmp_re*W_re - tmp_im*W_im)>>15;
        zptr[1+(n<<1)] = -(tmp_re*W_im + tmp_im*W_re)>>15;

#ifdef DEBUG_PUCCH_RX
        printf("[eNB] PUCCH subframe %d z(%d,%d) => %d,%d, alpha(%d) => %d,%d\n",subframe,l,n,zptr[n<<1],zptr[(n<<1)+1],
              alpha_ind,alpha_re[alpha_ind],alpha_im[alpha_ind]);
#endif

        alpha_ind = (alpha_ind + n_cs)%12;
      } // n

      zptr+=24;
    } // l

    nprime=nprime1;
    n_oc  =n_oc1;
  } // ns

  rem = ((((deltaPUCCH_Shift*Ncs1_div_deltaPUCCH_Shift)>>3)&7)>0) ? 1 : 0;

  m = (n1_pucch < thres) ? NRB2 : (((n1_pucch-thres)/(12*c/deltaPUCCH_Shift))+NRB2+((deltaPUCCH_Shift*Ncs1_div_deltaPUCCH_Shift)>>3)+rem);

#ifdef DEBUG_PUCCH_RX
  printf("[eNB] PUCCH: m %d\n",m);
#endif
  nsymb = N_UL_symb<<1;

  zptr = (int16_t*)z;

  // Do detection
  for (aa=0; aa<frame_parms->nb_antennas_rx; aa++) {

    //for (j=0,l=0;l<(nsymb-1);l++) {
    for (j=0,l=0; l<nsymb; l++) {
      if ((l<(nsymb>>1)) && ((m&1) == 0))
        re_offset = (m*6) + frame_parms->first_carrier_offset;
      else if ((l<(nsymb>>1)) && ((m&1) == 1))
        re_offset = frame_parms->first_carrier_offset + (frame_parms->N_RB_DL - (m>>1) - 1)*12;
      else if ((m&1) == 0)
        re_offset = frame_parms->first_carrier_offset + (frame_parms->N_RB_DL - (m>>1) - 1)*12;
      else
        re_offset = ((m-1)*6) + frame_parms->first_carrier_offset;

      if (re_offset > frame_parms->ofdm_symbol_size)
        re_offset -= (frame_parms->ofdm_symbol_size);

      symbol_offset = (unsigned int)frame_parms->ofdm_symbol_size*l;
      rxptr = (int16_t *)&common_vars->rxdataF[0][aa][symbol_offset];

      for (i=0; i<12; i++,j+=2,re_offset++) {
        if (re_offset==frame_parms->ofdm_symbol_size)
          re_offset = 0;

        rxcomp[aa][j]   = (int16_t)((rxptr[re_offset<<1]*(int32_t)zptr[j])>>15)   - ((rxptr[1+(re_offset<<1)]*(int32_t)zptr[1+j])>>15);
        rxcomp[aa][1+j] = (int16_t)((rxptr[re_offset<<1]*(int32_t)zptr[1+j])>>15) + ((rxptr[1+(re_offset<<1)]*(int32_t)zptr[j])>>15);

#ifdef DEBUG_PUCCH_RX
        printf("[eNB] PUCCH subframe %d (%d,%d,%d,%d,%d) => (%d,%d) x (%d,%d) : (%d,%d)\n",subframe,l,i,re_offset,m,j,
              rxptr[re_offset<<1],rxptr[1+(re_offset<<1)],
              zptr[j],zptr[1+j],
              rxcomp[aa][j],rxcomp[aa][1+j]);
#endif
      } //re
    } // symbol
  }  // antenna


  // PUCCH Format 1
  // Do cfo correction and MRC across symbols

  if (fmt == pucch_format1) {
#ifdef DEBUG_PUCCH_RX
    printf("Doing PUCCH detection for format 1\n");
#endif

    stat_max = 0;


    for (phase=0; phase<7; phase++) {
      stat=0;

      for (aa=0; aa<frame_parms->nb_antennas_rx; aa++) {
        for (re=0; re<12; re++) {
          stat_re=0;
          stat_im=0;
          off=re<<1;
          cfo =  (frame_parms->Ncp==0) ? &cfo_pucch_np[14*phase] : &cfo_pucch_ep[12*phase];

          for (l=0; l<(nsymb>>1); l++) {
            stat_re += (((rxcomp[aa][off]*(int32_t)cfo[l<<1])>>15)     - ((rxcomp[aa][1+off]*(int32_t)cfo[1+(l<<1)])>>15))/nsymb;
            stat_im += (((rxcomp[aa][off]*(int32_t)cfo[1+(l<<1)])>>15) + ((rxcomp[aa][1+off]*(int32_t)cfo[(l<<1)])>>15))/nsymb;
            off+=2;

		    
#ifdef DEBUG_PUCCH_RX
            printf("[eNB] PUCCH subframe %d (%d,%d,%d) => (%d,%d) x (%d,%d) : (%d,%d) , stat %d\n",subframe,phase,l,re,
                  rxcomp[aa][off],rxcomp[aa][1+off],
                  cfo[l<<1],cfo[1+(l<<1)],
                  stat_re,stat_im,stat);
#endif
          }

          for (l2=0,l=(nsymb>>1); l<(nsymb-1); l++,l2++) {
            stat_re += (((rxcomp[aa][off]*(int32_t)cfo[l2<<1])>>15)     - ((rxcomp[aa][1+off]*(int32_t)cfo[1+(l2<<1)])>>15))/nsymb;
            stat_im += (((rxcomp[aa][off]*(int32_t)cfo[1+(l2<<1)])>>15) + ((rxcomp[aa][1+off]*(int32_t)cfo[(l2<<1)])>>15))/nsymb;
            off+=2;

#ifdef DEBUG_PUCCH_RX
            printf("[eNB] PUCCH subframe %d (%d,%d,%d) => (%d,%d) x (%d,%d) : (%d,%d), stat %d\n",subframe,phase,l2,re,
                  rxcomp[aa][off],rxcomp[aa][1+off],
                  cfo[l2<<1],cfo[1+(l2<<1)],
                  stat_re,stat_im,stat);
#endif


          }
	  stat += ((stat_re*stat_re) + (stat_im*stat_im));

       } //re
      } // aa

 
      if (stat>stat_max) {
        stat_max = stat;
        phase_max = phase;
      }

    } //phase

//    stat_max *= nsymb;  // normalize to energy per symbol
//    stat_max /= (frame_parms->N_RB_UL*12); // 
    stat_max /= (nsymb*12);
#ifdef DEBUG_PUCCH_RX
    printf("[eNB] PUCCH: stat %d, stat_max %d, phase_max %d\n", stat,stat_max,phase_max);
#endif

#ifdef DEBUG_PUCCH_RX
    LOG_I(PHY,"[eNB] PUCCH fmt1:  stat_max : %d, sigma2_dB %d (%d, %d), phase_max : %d\n",dB_fixed(stat_max),sigma2_dB,eNB->measurements[0].n0_subband_power_tot_dBm[6],pucch1_thres,phase_max);
#endif

    eNB->pucch1_stats[UE_id][(subframe<<10)+eNB->pucch1_stats_cnt[UE_id][subframe]] = stat_max;
    eNB->pucch1_stats_thres[UE_id][(subframe<<10)+eNB->pucch1_stats_cnt[UE_id][subframe]] = sigma2_dB+pucch1_thres;
    eNB->pucch1_stats_cnt[UE_id][subframe] = (eNB->pucch1_stats_cnt[UE_id][subframe]+1)&1023;

    T(T_ENB_PHY_PUCCH_1_ENERGY, T_INT(eNB->Mod_id), T_INT(UE_id), T_INT(frame), T_INT(subframe),
      T_INT(stat_max), T_INT(sigma2_dB+pucch1_thres));

    /*
    if (eNB->pucch1_stats_cnt[UE_id][subframe] == 0) {
      write_output("pucch_debug.m","pucch_energy",
		   &eNB->pucch1_stats[UE_id][(subframe<<10)],
		   1024,1,2);
      AssertFatal(0,"Exiting for PUCCH 1 debug\n");

    }
    */

    // This is a moving average of the PUCCH1 statistics conditioned on being above or below the threshold
    if (sigma2_dB<(dB_fixed(stat_max)-pucch1_thres))  {
      *payload = 1;
      *Po_PUCCH1_above = ((*Po_PUCCH1_above<<9) + (stat_max<<9)+1024)>>10;
      //LOG_I(PHY,"[eNB] PUCCH fmt1:  stat_max : %d, sigma2_dB %d (%d, %d), phase_max : %d\n",dB_fixed(stat_max),sigma2_dB,eNB->PHY_measurements_eNB[0].n0_power_tot_dBm,pucch1_thres,phase_max);
    }
    else {
      *payload = 0;
      *Po_PUCCH1_below = ((*Po_PUCCH1_below<<9) + (stat_max<<9)+1024)>>10;
    }
    //printf("[eNB] PUCCH fmt1:  stat_max : %d, sigma2_dB %d (I0 %d dBm, thres %d), Po_PUCCH1_below/above : %d / %d\n",dB_fixed(stat_max),sigma2_dB,eNB->measurements[0].n0_subband_power_tot_dBm[6],pucch1_thres,dB_fixed(*Po_PUCCH1_below),dB_fixed(*Po_PUCCH1_above));
    *Po_PUCCH_update = 1;
    if (UE_id==0) {
      VCD_SIGNAL_DUMPER_DUMP_VARIABLE_BY_NAME(VCD_SIGNAL_DUMPER_VARIABLES_UE0_SR_ENERGY,dB_fixed(stat_max));
      VCD_SIGNAL_DUMPER_DUMP_VARIABLE_BY_NAME(VCD_SIGNAL_DUMPER_VARIABLES_UE0_SR_THRES,sigma2_dB+pucch1_thres);
    }
  } else if ((fmt == pucch_format1a)||(fmt == pucch_format1b)) {
    stat_max = 0;
#ifdef DEBUG_PUCCH_RX
    LOG_I(PHY,"Doing PUCCH detection for format 1a/1b\n");
#endif

    for (phase=0; phase<7; phase++) {
      stat=0;

      for (aa=0; aa<frame_parms->nb_antennas_rx; aa++) {
        for (re=0; re<12; re++) {
          stat_re=0;
          stat_im=0;
          stat_ref_re=0;
          stat_ref_im=0;
          off=re<<1;
          cfo =  (frame_parms->Ncp==0) ? &cfo_pucch_np[14*phase] : &cfo_pucch_ep[12*phase];


          for (l=0; l<(nsymb>>1); l++) {
            if ((l<2)||(l>(nsymb>>1) - 3)) {  //data symbols
              stat_re += ((rxcomp[aa][off]*(int32_t)cfo[l<<1])>>15)     - ((rxcomp[aa][1+off]*(int32_t)cfo[1+(l<<1)])>>15);
              stat_im += ((rxcomp[aa][off]*(int32_t)cfo[1+(l<<1)])>>15) + ((rxcomp[aa][1+off]*(int32_t)cfo[(l<<1)])>>15);
            } else { //reference symbols
              stat_ref_re += ((rxcomp[aa][off]*(int32_t)cfo[l<<1])>>15)     - ((rxcomp[aa][1+off]*(int32_t)cfo[1+(l<<1)])>>15);
              stat_ref_im += ((rxcomp[aa][off]*(int32_t)cfo[1+(l<<1)])>>15) + ((rxcomp[aa][1+off]*(int32_t)cfo[(l<<1)])>>15);
            }

            off+=2;
#ifdef DEBUG_PUCCH_RX
            printf("[eNB] PUCCH subframe %d (%d,%d) => (%d,%d) x (%d,%d) : (%d,%d)\n",subframe,l,re,
                  rxcomp[aa][off],rxcomp[aa][1+off],
                  cfo[l<<1],cfo[1+(l<<1)],
                  stat_re,stat_im);
#endif
          }




          for (l2=0,l=(nsymb>>1); l<(nsymb-1); l++,l2++) {
            if ((l2<2) || ((l2>(nsymb>>1) - 3)) ) {  // data symbols
              stat_re += ((rxcomp[aa][off]*(int32_t)cfo[l2<<1])>>15)     - ((rxcomp[aa][1+off]*(int32_t)cfo[1+(l2<<1)])>>15);
              stat_im += ((rxcomp[aa][off]*(int32_t)cfo[1+(l2<<1)])>>15) + ((rxcomp[aa][1+off]*(int32_t)cfo[(l2<<1)])>>15);
            } else { //reference_symbols
              stat_ref_re += ((rxcomp[aa][off]*(int32_t)cfo[l<<1])>>15)     - ((rxcomp[aa][1+off]*(int32_t)cfo[1+(l<<1)])>>15);
              stat_ref_im += ((rxcomp[aa][off]*(int32_t)cfo[1+(l<<1)])>>15) + ((rxcomp[aa][1+off]*(int32_t)cfo[(l<<1)])>>15);
            }

            off+=2;
#ifdef DEBUG_PUCCH_RX
            printf("[eNB] PUCCH subframe %d (%d,%d) => (%d,%d) x (%d,%d) : (%d,%d)\n",subframe,l2,re,
                  rxcomp[aa][off],rxcomp[aa][1+off],
                  cfo[l2<<1],cfo[1+(l2<<1)],
                  stat_re,stat_im);
#endif

          }

#ifdef DEBUG_PUCCH_RX
          printf("aa%d re %d : phase %d : stat %d\n",aa,re,phase,stat);
#endif

	  stat += ((((stat_re*stat_re)) + ((stat_im*stat_im)) +
		    ((stat_ref_re*stat_ref_re)) + ((stat_ref_im*stat_ref_im)))/nsymb);


        } //re
      } // aa

#ifdef DEBUG_PUCCH_RX
      LOG_I(PHY,"Format 1A: phase %d : stat %d\n",phase,stat);
#endif
      if (stat>stat_max) {
        stat_max = stat;
        phase_max = phase;
      }
    } //phase

    stat_max/=(12);  //normalize to energy per symbol and RE
#ifdef DEBUG_PUCCH_RX
    printf("[eNB] PUCCH fmt1a/b:  stat_max : %d, phase_max : %d\n",stat_max,phase_max);
#endif

    stat_re=0;
    stat_im=0;
    //    printf("PUCCH1A : Po_PUCCH before %d dB (%d)\n",dB_fixed(*Po_PUCCH),*Po_PUCCH);
    *Po_PUCCH = ((*Po_PUCCH>>1) + ((stat_max)>>1));
    *Po_PUCCH_dBm = dB_fixed(*Po_PUCCH/frame_parms->N_RB_UL) - eNB->rx_total_gain_dB;
    *Po_PUCCH_update = 1;
    /*
    printf("PUCCH1A : stat_max %d (%d,%d,%d) => Po_PUCCH %d\n",
	   dB_fixed(stat_max),
	   pucch1_thres+sigma2_dB,
	   pucch1_thres,
	   sigma2_dB,
	   dB_fixed(*Po_PUCCH));
    */
    // Do detection now
    if (sigma2_dB<(dB_fixed(stat_max)-pucch1_thres))  {//


      *Po_PUCCH = ((*Po_PUCCH*1023) + stat_max)>>10;

      chL = (nsymb>>1)-4;

      for (aa=0; aa<frame_parms->nb_antennas_rx; aa++) {
        for (re=0; re<12; re++) {
          chest_re=0;
          chest_im=0;
          cfo =  (frame_parms->Ncp==0) ? &cfo_pucch_np[14*phase_max] : &cfo_pucch_ep[12*phase_max];

          // channel estimate for first slot
          for (l=2; l<(nsymb>>1)-2; l++) {
            off=(re<<1) + (24*l);
            chest_re += (((rxcomp[aa][off]*(int32_t)cfo[l<<1])>>15)     - ((rxcomp[aa][1+off]*(int32_t)cfo[1+(l<<1)])>>15))/chL;
	    chest_im += (((rxcomp[aa][off]*(int32_t)cfo[1+(l<<1)])>>15) + ((rxcomp[aa][1+off]*(int32_t)cfo[(l<<1)])>>15))/chL;
          }

#ifdef DEBUG_PUCCH_RX
          printf("[eNB] PUCCH subframe %d l %d re %d chest1 => (%d,%d)\n",subframe,l,re,
                chest_re,chest_im);
#endif

          for (l=0; l<2; l++) {
            off=(re<<1) + (24*l);
            tmp_re = ((rxcomp[aa][off]*(int32_t)cfo[l<<1])>>15)     - ((rxcomp[aa][1+off]*(int32_t)cfo[1+(l<<1)])>>15);
            tmp_im = ((rxcomp[aa][off]*(int32_t)cfo[1+(l<<1)])>>15) + ((rxcomp[aa][1+off]*(int32_t)cfo[(l<<1)])>>15);
            stat_re += (((tmp_re*chest_re)>>15) + ((tmp_im*chest_im)>>15))/4;
            stat_im += (((tmp_re*chest_im)>>15) - ((tmp_im*chest_re)>>15))/4;
            off+=2;
#ifdef DEBUG_PUCCH_RX
            printf("[eNB] PUCCH subframe %d (%d,%d) => (%d,%d) x (%d,%d) : (%d,%d)\n",subframe,l,re,
                  rxcomp[aa][off],rxcomp[aa][1+off],
                  cfo[l<<1],cfo[1+(l<<1)],
                  stat_re,stat_im);
#endif
          }

          for (l=(nsymb>>1)-2; l<(nsymb>>1); l++) {
            off=(re<<1) + (24*l);
            tmp_re = ((rxcomp[aa][off]*(int32_t)cfo[l<<1])>>15)     - ((rxcomp[aa][1+off]*(int32_t)cfo[1+(l<<1)])>>15);
            tmp_im = ((rxcomp[aa][off]*(int32_t)cfo[1+(l<<1)])>>15) + ((rxcomp[aa][1+off]*(int32_t)cfo[(l<<1)])>>15);
            stat_re += (((tmp_re*chest_re)>>15) + ((tmp_im*chest_im)>>15))/4;
            stat_im += (((tmp_re*chest_im)>>15) - ((tmp_im*chest_re)>>15))/4;
            off+=2;
#ifdef DEBUG_PUCCH_RX
            printf("[eNB] PUCCH subframe %d (%d,%d) => (%d,%d) x (%d,%d) : (%d,%d)\n",subframe,l,re,
                  rxcomp[aa][off],rxcomp[aa][1+off],
                  cfo[l<<1],cfo[1+(l<<1)],
                  stat_re,stat_im);
#endif
          }

          chest_re=0;
          chest_im=0;

          // channel estimate for second slot
          for (l=2; l<(nsymb>>1)-2; l++) {
            off=(re<<1) + (24*l) + (nsymb>>1)*24;
            chest_re += (((rxcomp[aa][off]*(int32_t)cfo[l<<1])>>15)     - ((rxcomp[aa][1+off]*(int32_t)cfo[1+(l<<1)])>>15))/chL;
	    chest_im += (((rxcomp[aa][off]*(int32_t)cfo[1+(l<<1)])>>15) + ((rxcomp[aa][1+off]*(int32_t)cfo[(l<<1)])>>15))/chL;
          }

#ifdef DEBUG_PUCCH_RX
          printf("[eNB] PUCCH subframe %d l %d re %d chest2 => (%d,%d)\n",subframe,l,re,
                chest_re,chest_im);
#endif

          for (l=0; l<2; l++) {
            off=(re<<1) + (24*l) + (nsymb>>1)*24;
            tmp_re = ((rxcomp[aa][off]*(int32_t)cfo[l<<1])>>15)     - ((rxcomp[aa][1+off]*(int32_t)cfo[1+(l<<1)])>>15);
            tmp_im = ((rxcomp[aa][off]*(int32_t)cfo[1+(l<<1)])>>15) + ((rxcomp[aa][1+off]*(int32_t)cfo[(l<<1)])>>15);
            stat_re += (((tmp_re*chest_re)>>15) + ((tmp_im*chest_im)>>15))/4;
            stat_im += (((tmp_re*chest_im)>>15) - ((tmp_im*chest_re)>>15))/4;
            off+=2;
#ifdef DEBUG_PUCCH_RX
            printf("[PHY][eNB] PUCCH subframe %d (%d,%d) => (%d,%d) x (%d,%d) : (%d,%d)\n",subframe,l,re,
                  rxcomp[aa][off],rxcomp[aa][1+off],
                  cfo[l<<1],cfo[1+(l<<1)],
                  stat_re,stat_im);
#endif
          }

          for (l=(nsymb>>1)-2; l<(nsymb>>1)-1; l++) {
            off=(re<<1) + (24*l) + (nsymb>>1)*24;
            tmp_re = ((rxcomp[aa][off]*(int32_t)cfo[l<<1])>>15)     - ((rxcomp[aa][1+off]*(int32_t)cfo[1+(l<<1)])>>15);
            tmp_im = ((rxcomp[aa][off]*(int32_t)cfo[1+(l<<1)])>>15) + ((rxcomp[aa][1+off]*(int32_t)cfo[(l<<1)])>>15);
            stat_re += (((tmp_re*chest_re)>>15) + ((tmp_im*chest_im)>>15))/4;
            stat_im += (((tmp_re*chest_im)>>15) - ((tmp_im*chest_re)>>15))/4;
            off+=2;
#ifdef DEBUG_PUCCH_RX
            printf("[PHY][eNB] PUCCH subframe %d (%d,%d) => (%d,%d) x (%d,%d) : (%d,%d)\n",subframe,l,re,
                  rxcomp[aa][off],rxcomp[aa][1+off],
                  cfo[l<<1],cfo[1+(l<<1)],
                  stat_re,stat_im);
#endif
          }

#ifdef DEBUG_PUCCH_RX
          printf("aa%d re %d : stat %d,%d\n",aa,re,stat_re,stat_im);
#endif

        } //re
      } // aa

#ifdef DEBUG_PUCCH_RX
      LOG_I(PHY,"PUCCH 1a/b: subframe %d : stat %d,%d (pos %d)\n",subframe,stat_re,stat_im,
	    (subframe<<10) + (eNB->pucch1ab_stats_cnt[UE_id][subframe]));
#endif

	eNB->pucch1ab_stats[UE_id][(subframe<<11) + 2*(eNB->pucch1ab_stats_cnt[UE_id][subframe])] = (stat_re);
	eNB->pucch1ab_stats[UE_id][(subframe<<11) + 1+2*(eNB->pucch1ab_stats_cnt[UE_id][subframe])] = (stat_im);
	eNB->pucch1ab_stats_cnt[UE_id][subframe] = (eNB->pucch1ab_stats_cnt[UE_id][subframe]+1)&1023;

      /* frame not available here - set to -1 for the moment */
      T(T_ENB_PHY_PUCCH_1AB_IQ, T_INT(eNB->Mod_id), T_INT(UE_id), T_INT(-1), T_INT(subframe), T_INT(stat_re), T_INT(stat_im));

	  
      *payload = (stat_re<0) ? 1 : 0;

      if (fmt==pucch_format1b)
        *(1+payload) = (stat_im<0) ? 1 : 0;
    } else { // insufficient energy on PUCCH so NAK
      *payload = 0;
      ((int16_t*)&eNB->pucch1ab_stats[UE_id][(subframe<<10) + (eNB->pucch1ab_stats_cnt[UE_id][subframe])])[0] = (int16_t)(stat_re);
      ((int16_t*)&eNB->pucch1ab_stats[UE_id][(subframe<<10) + (eNB->pucch1ab_stats_cnt[UE_id][subframe])])[1] = (int16_t)(stat_im);
      eNB->pucch1ab_stats_cnt[UE_id][subframe] = (eNB->pucch1ab_stats_cnt[UE_id][subframe]+1)&1023;

      if (fmt==pucch_format1b)
        *(1+payload) = 0;
    }
  } else {
    LOG_E(PHY,"[eNB] PUCCH fmt2/2a/2b not supported\n");
  }
  
  /* PUCCH format3 >> */
  } else {
    /* SubCarrier Demap */
    Ret = pucchfmt3_subCarrierDeMapping( eNB, SubCarrierDeMapData, n3_pucch );
    if(Ret != 0) {
        //***log pucchfmt3_subCarrierDeMapping Error!
        return(-1);
    }
    
    /* cyclic shift hopping remove */
    Ret = pucchfmt3_Baseseq_csh_remove( SubCarrierDeMapData, CshData_fmt3, frame_parms, subframe, eNB->ncs_cell );
    if(Ret != 0) {
        //***log pucchfmt3_Baseseq_csh_remove Error!
        return(-1);
    }
    
    /* Channel Estimation */
    Ret = pucchfmt3_ChannelEstimation( SubCarrierDeMapData, delta_theta, ChestValue, &Interpw, subframe, shortened_format, frame_parms, n3_pucch, n3_pucch_array, eNB->ncs_cell );
    if(Ret != 0) {
        //***log pucchfmt3_ChannelEstimation Error!
        return(-1);
    }
    
    /* Channel Equalization */
    Ret = pucchfmt3_Equalization( CshData_fmt3, ChdetAfterValue_fmt3, ChestValue, frame_parms );
    if(Ret != 0) {
        //***log pucchfmt3_Equalization Error!
        return(-1);
    }
    
    /* Frequency deviation remove AFC */
    Ret = pucchfmt3_FrqDevRemove( ChdetAfterValue_fmt3, delta_theta, RemoveFrqDev_fmt3, frame_parms );
    if(Ret != 0) {
        //***log pucchfmt3_FrqDevRemove Error!
        return(-1);
    }
    
    /* orthogonal sequence remove */
    Ret = pucchfmt3_OrthSeqRemove( RemoveFrqDev_fmt3, Fmt3xDataRmvOrth, shortened_format, n3_pucch, frame_parms );
    if(Ret != 0) {
        //***log pucchfmt3_OrthSeqRemove Error!
        return(-1);
    }
    
    /* averaging antenna */
    pucchfmt3_AvgAnt( Fmt3xDataRmvOrth, Fmt3xDataAvgAnt, shortened_format, frame_parms );
    
    /* averaging symbol */
    pucchfmt3_AvgSym( Fmt3xDataAvgAnt, Fmt3xDataAvgSym, shortened_format );
    
    /* IDFT */
    pucchfmt3_IDft2( (int16_t*)Fmt3xDataAvgSym[0], (int16_t*)IFFTOutData_Fmt3[0] );
    pucchfmt3_IDft2( (int16_t*)Fmt3xDataAvgSym[1], (int16_t*)IFFTOutData_Fmt3[1] );
    
    /* descramble */
    pucchfmt3_Descramble(IFFTOutData_Fmt3, b, subframe, frame_parms->Nid_cell, crnti);

    /* Is payload 6bit or 7bit? */
    if( do_sr == 1 ) {
        payload_max = 7;
    } else {
        payload_max = 6;
    }
    
    /* decode */
    payload_entity = pucchfmt3_Decode( b, subframe, DTXthreshold, Interpw, do_sr );
    if (payload_entity == -1) {
        //***log pucchfmt3_Decode Error!
        return(-1);
    }
    
    for(i=0; i<payload_max; i++) {
      *(payload+i) = (uint8_t)((payload_entity>>i) & 0x01);
    }
  }
  /* PUCCH format3 << */

  return((int32_t)stat_max);

}


int32_t rx_pucch_emul(PHY_VARS_eNB *eNB,
		      eNB_rxtx_proc_t *proc,
                      uint8_t UE_index,
                      PUCCH_FMT_t fmt,
                      uint8_t n1_pucch_sel,
                      uint8_t *payload)

{
  uint8_t UE_id;
  uint16_t rnti;
  int subframe = proc->subframe_rx;
  uint8_t CC_id = eNB->CC_id;

  rnti = eNB->ulsch[UE_index]->rnti;

  for (UE_id=0; UE_id<NB_UE_INST; UE_id++) {
    if (rnti == PHY_vars_UE_g[UE_id][CC_id]->pdcch_vars[PHY_vars_UE_g[UE_id][CC_id]->current_thread_id[subframe]][0]->crnti)
      break;
  }

  if (UE_id==NB_UE_INST) {
    LOG_W(PHY,"rx_pucch_emul: Didn't find UE with rnti %x\n",rnti);
    return(-1);
  }

  if (fmt == pucch_format1) {
    payload[0] = PHY_vars_UE_g[UE_id][CC_id]->sr[subframe];
  } else if (fmt == pucch_format1a) {
    payload[0] = PHY_vars_UE_g[UE_id][CC_id]->pucch_payload[0];
  } else if (fmt == pucch_format1b) {
    payload[0] = PHY_vars_UE_g[UE_id][CC_id]->pucch_payload[0];
    payload[1] = PHY_vars_UE_g[UE_id][CC_id]->pucch_payload[1];
  } else
    LOG_E(PHY,"[eNB] Frame %d: Can't handle formats 2/2a/2b\n",proc->frame_rx);

  if (PHY_vars_UE_g[UE_id][CC_id]->pucch_sel[subframe] == n1_pucch_sel)
    return(99);
  else
    return(0);
}
