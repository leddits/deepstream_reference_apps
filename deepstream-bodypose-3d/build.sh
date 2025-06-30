#!/bin/bash

# 3D Body Pose DeepStream 애플리케이션 자동 빌드 스크립트
# CUDA 버전을 자동으로 감지하여 빌드합니다.

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== 3D Body Pose DeepStream 애플리케이션 빌드 시작 ===${NC}"

# CUDA 버전 자동 감지
if [ -z "$CUDA_VER" ]; then
    CUDA_VER=$(nvcc --version | grep "release" | sed 's/.*release \([0-9]*\.[0-9]*\).*/\1/')
    if [ -z "$CUDA_VER" ]; then
        echo -e "${RED}오류: CUDA 버전을 자동으로 감지할 수 없습니다.${NC}"
        echo -e "${YELLOW}CUDA_VER 환경변수를 수동으로 설정해주세요. 예: export CUDA_VER=12.6${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}감지된 CUDA 버전: ${CUDA_VER}${NC}"

# 프로젝트 홈 디렉토리 설정
BODYPOSE3D_HOME=$(pwd)
export BODYPOSE3D_HOME

echo -e "${GREEN}프로젝트 홈: ${BODYPOSE3D_HOME}${NC}"

# 1. Custom nvinfer parser 빌드
echo -e "${YELLOW}1. Custom nvinfer parser 빌드 중...${NC}"
cd $BODYPOSE3D_HOME/sources/nvdsinfer_custom_impl_BodyPose3DNet
make clean
make CUDA_VER=$CUDA_VER

if [ ! -f "libnvdsinfer_custom_impl_BodyPose3DNet.so" ]; then
    echo -e "${RED}오류: Custom nvinfer parser 빌드 실패${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Custom nvinfer parser 빌드 완료${NC}"

# 2. 메인 애플리케이션 빌드
echo -e "${YELLOW}2. 메인 애플리케이션 빌드 중...${NC}"
cd $BODYPOSE3D_HOME/sources
make clean
make CUDA_VER=$CUDA_VER

if [ ! -f "deepstream-pose-estimation-app" ]; then
    echo -e "${RED}오류: 메인 애플리케이션 빌드 실패${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 메인 애플리케이션 빌드 완료${NC}"

# 빌드 완료 메시지
echo -e "${GREEN}=== 빌드 완료! ===${NC}"
echo -e "${GREEN}실행 파일: ${BODYPOSE3D_HOME}/sources/deepstream-pose-estimation-app${NC}"
echo -e "${GREEN}라이브러리: ${BODYPOSE3D_HOME}/sources/nvdsinfer_custom_impl_BodyPose3DNet/libnvdsinfer_custom_impl_BodyPose3DNet.so${NC}"
echo ""
echo -e "${YELLOW}사용법:${NC}"
echo -e "  cd ${BODYPOSE3D_HOME}/sources"
echo -e "  ./deepstream-pose-estimation-app --input file://${BODYPOSE3D_HOME}/streams/bodypose.mp4"
