# JavaScript 스크립트들
GET_LOCATION_JS = """
async () => {
    return await new Promise((resolve) => {
        if (!navigator.geolocation) {
            const errorJson = JSON.stringify({ 
                error: "이 브라우저는 위치 서비스를 지원하지 않습니다." 
            });
            resolve(errorJson);
        } else {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    console.log("위치 획득 성공:", position);
                    const locationJson = JSON.stringify({
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        accuracy: position.coords.accuracy
                    });
                    console.log("반환할 JSON:", locationJson);
                    resolve(locationJson);
                },
                (error) => {
                    console.error("위치 획득 실패:", error);
                    let errorMsg = "위치 정보를 가져올 수 없습니다: ";
                    switch(error.code) {
                        case 1:
                            errorMsg += "위치 접근 권한이 거부되었습니다.";
                            break;
                        case 2:
                            errorMsg += "위치 정보를 사용할 수 없습니다.";
                            break;
                        case 3:
                            errorMsg += "위치 요청 시간이 초과되었습니다.";
                            break;
                        default:
                            errorMsg += error.message || "알 수 없는 오류가 발생했습니다.";
                            break;
                    }
                    const errorJson = JSON.stringify({ error: errorMsg });
                    resolve(errorJson);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 300000
                }
            );
        }
    });
}
"""

# 앱 설정
APP_CONFIG = {
    "title": "무더위 쉼터 찾기",
    "theme": "soft",
    "share": True,
    "server_name": "0.0.0.0",
    "server_port": 7860,
}

# UI 텍스트
UI_TEXT = {
    "main_title": "# 🏠 무더위 쉼터 위치 조회 및 가까운 쉼터 알리미",
    "location_section": "## 📍 내 위치 입력",
    "location_guide": "💡 **안내:** 현재 위치 가져오기를 하면 자치구 필터가 자동으로 설정됩니다!",
    "map_section": "## 🗺️ 쉼터 지도",
    "nearby_section": "## 📋 주변 쉼터 목록 (1km 이내)",
    "filter_section": "## 🔍 필터 설정",
    "get_location_btn": "📍 현재 위치 가져오기",
    "update_btn": "🔄 지도 업데이트",
    "location_status_default": "현재 위치 버튼을 클릭해주세요",
}

# 기본 좌표 (서울시청)
DEFAULT_COORDINATES = {"latitude": 37.5665, "longitude": 126.9780}

# 필터 라벨
FILTER_LABELS = {
    "facility_type": "시설구분",
    "area_size": "시설면적",
    "capacity_size": "이용가능인원",
    "fan_filter": "선풍기",
    "ac_filter": "에어컨",
    "district": "자치구 (📍 위치 기반 자동 설정)",
}
