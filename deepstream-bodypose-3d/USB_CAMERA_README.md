# USB Camera Support for DeepStream BodyPose3D Application

이 애플리케이션은 USB 카메라를 입력 소스로 사용할 수 있도록 수정되었습니다.

## 기능

- USB 카메라 입력 지원 (v4l2src 기반)
- 실시간 3D 포즈 추정
- 자동 소스 검출 (USB 카메라 vs 파일/URI)

## 사용법

### USB 카메라 사용

```bash
./deepstream-pose-estimation-app --input /dev/video0
```

### 추가 옵션

```bash
# 출력 비디오 저장
./deepstream-pose-estimation-app --input /dev/video0 --output output.mp4

# 포즈 데이터 JSON 파일로 저장
./deepstream-pose-estimation-app --input /dev/video0 --save-pose poses.json

# FPS 표시
./deepstream-pose-estimation-app --input /dev/video0 --fps

# 해상도 설정 (기본값: 1280x720)
./deepstream-pose-estimation-app --input /dev/video0 --width 640 --height 480
```

### 카메라 장치 확인

사용 가능한 카메라 장치를 확인하려면:

```bash
ls /dev/video*
v4l2-ctl --list-devices
```

## 지원되는 카메라 형식

- USB UVC 호환 카메라
- 기본 캡처 형식: YUY2 (640x480@30fps)
- 자동 형식 변환: YUY2 -> NV12 -> NVMM

## 문제 해결

### 카메라를 찾을 수 없는 경우
```bash
# 카메라 권한 확인
sudo chmod 666 /dev/video0

# 카메라가 다른 애플리케이션에서 사용 중인지 확인
lsof /dev/video0
```

### 성능 최적화
- 더 높은 프레임레이트를 위해 해상도를 낮추세요
- GPU 가속을 위해 NVMM 메모리를 사용합니다
- 실시간 처리를 위해 `live-source=true` 설정이 적용됩니다

## 기술적 세부사항

수정된 부분:
1. `create_usb_camera_source_bin()` 함수 추가
2. USB 카메라 자동 검출 로직
3. v4l2src 기반 파이프라인 구성
4. 실시간 스트리밍을 위한 live-source 설정

파이프라인 구조:
```
v4l2src -> capsfilter -> videoconvert -> capsfilter -> nvvideoconvert -> capsfilter -> streammux -> ...
```
