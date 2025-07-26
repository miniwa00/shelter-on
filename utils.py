import pandas as pd
import folium
import numpy as np
from math import radians, cos, sin, asin, sqrt
import re
import json


# 데이터 로드
def load_data():
    df = pd.read_csv("shelter_with_details_by_address_filtered.csv")

    # 숫자형 컬럼들
    numeric_columns = {
        "시설년도": "Int64",  # nullable integer
        "시설면적": "float64",
        "이용가능인원": "Int64",  # nullable integer
        "경도": "float64",
        "위도": "float64",
        "선풍기보유대수": "Int64",  # nullable integer
        "에어컨보유대수": "Int64",  # nullable integer
    }

    for col, dtype in numeric_columns.items():
        if col in df.columns:
            # 결측값이나 잘못된 데이터 처리
            df[col] = pd.to_numeric(df[col], errors="coerce").astype(dtype)

    # 문자열 컬럼들 (명시적으로 string 타입으로 변환)
    string_columns = [
        "위치코드",
        "시설구분1",
        "시설구분2",
        "쉼터명칭",
        "도로명주소",
        "지번주소",
        "비고",
        "야간운영여부",
        "휴일운영여부",
        "숙박가능여부",
        "관리부서명",
        "관리부서전화번호",
    ]

    for col in string_columns:
        if col in df.columns:
            df[col] = df[col].astype("string")
            # 빈 문자열을 NaN으로 변환
            df[col] = df[col].replace("", pd.NA)

    # Boolean 형태의 컬럼들 정규화 (Y/N, 예/아니오 등을 표준화)
    boolean_columns = ["야간운영여부", "휴일운영여부", "숙박가능여부"]

    for col in boolean_columns:
        if col in df.columns:
            # 다양한 형태의 Yes/No 값들을 표준화
            df[col] = df[col].str.strip()  # 공백 제거
            df[col] = df[col].replace(
                {
                    "Y": "예",
                    "N": "아니오",
                    "y": "예",
                    "n": "아니오",
                    "YES": "예",
                    "NO": "아니오",
                    "yes": "예",
                    "no": "아니오",
                    "1": "예",
                    "0": "아니오",
                    "True": "예",
                    "False": "아니오",
                    "true": "예",
                    "false": "아니오",
                }
            )

    # 데이터 검증 및 정리
    # 좌표값이 서울 범위를 벗어나는 경우 필터링 (대략적인 서울 범위)
    seoul_lat_range = (37.4, 37.7)
    seoul_lon_range = (126.7, 127.2)

    # 좌표가 서울 범위를 벗어나는 경우 NaN으로 처리
    invalid_coords = (
        (df["위도"] < seoul_lat_range[0])
        | (df["위도"] > seoul_lat_range[1])
        | (df["경도"] < seoul_lon_range[0])
        | (df["경도"] > seoul_lon_range[1])
    )
    df.loc[invalid_coords, ["위도", "경도"]] = pd.NA

    # 음수값이 있으면 안 되는 컬럼들 검증
    positive_columns = ["시설면적", "이용가능인원", "선풍기보유대수", "에어컨보유대수"]
    for col in positive_columns:
        if col in df.columns:
            df.loc[df[col] < 0, col] = pd.NA

    # 시설년도가 현실적이지 않은 경우 필터링 (1900년 이후, 현재년도 이후 제외)
    current_year = pd.Timestamp.now().year
    if "시설년도" in df.columns:
        invalid_years = (df["시설년도"] < 1900) | (df["시설년도"] > current_year)
        df.loc[invalid_years, "시설년도"] = pd.NA

    return df


# 거리 계산 함수 (하버사인 공식)
def haversine(lon1, lat1, lon2, lat2):
    """두 지점 간의 거리를 킬로미터 단위로 계산"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * asin(sqrt(a)) * 6371  # 지구 반지름 6371km


# 데이터 전처리 함수들
def categorize_area(area):
    """시설면적을 5단계로 분류"""
    if pd.isna(area):
        return "정보없음"
    if area < 50:
        return "매우 작음"
    elif area < 100:
        return "작음"
    elif area < 200:
        return "보통"
    elif area < 500:
        return "큼"
    else:
        return "매우 큼"


def categorize_capacity(capacity):
    """이용가능인원을 5단계로 분류"""
    if pd.isna(capacity):
        return "정보없음"
    if capacity < 10:
        return "매우 적음"
    elif capacity < 30:
        return "적음"
    elif capacity < 50:
        return "보통"
    elif capacity < 100:
        return "많음"
    else:
        return "매우 많음"


def has_fan(fan_count):
    """선풍기 보유 여부"""
    if pd.isna(fan_count) or fan_count == 0:
        return "없음"
    else:
        return "있음"


def has_ac(ac_count):
    """에어컨 보유 여부"""
    if pd.isna(ac_count) or ac_count == 0:
        return "없음"
    else:
        return "있음"


def extract_district(address):
    """도로명주소에서 자치구 추출"""
    if pd.isna(address):
        return "정보없음"

    # 서울시 자치구 패턴 매칭
    districts = [
        "강남구",
        "강동구",
        "강북구",
        "강서구",
        "관악구",
        "광진구",
        "구로구",
        "금천구",
        "노원구",
        "도봉구",
        "동대문구",
        "동작구",
        "마포구",
        "서대문구",
        "서초구",
        "성동구",
        "성북구",
        "송파구",
        "양천구",
        "영등포구",
        "용산구",
        "은평구",
        "종로구",
        "중구",
        "중랑구",
    ]

    for district in districts:
        if district in address:
            return district

    return "기타"


# 데이터 전처리
def preprocess_data(df):
    """데이터 전처리"""
    df["시설면적_분류"] = df["시설면적"].apply(categorize_area)
    df["이용가능인원_분류"] = df["이용가능인원"].apply(categorize_capacity)
    df["선풍기_여부"] = df["선풍기보유대수"].apply(has_fan)
    df["에어컨_여부"] = df["에어컨보유대수"].apply(has_ac)
    df["자치구"] = df["도로명주소"].apply(extract_district)

    return df


# 필터링 함수
def filter_data(
    df, facility_type, area_size, capacity_size, has_fan_filter, has_ac_filter, district
):
    """필터 조건에 따라 데이터 필터링 (멀티 선택 지원)"""
    filtered_df = df.copy()

    # 각 필터를 리스트로 변환 (단일 값인 경우)
    def ensure_list(value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    facility_type = ensure_list(facility_type)
    area_size = ensure_list(area_size)
    capacity_size = ensure_list(capacity_size)
    has_fan_filter = ensure_list(has_fan_filter)
    has_ac_filter = ensure_list(has_ac_filter)
    district = ensure_list(district)

    # 시설구분2 필터링
    if facility_type and "전체" not in facility_type:
        filtered_df = filtered_df[filtered_df["시설구분2"].isin(facility_type)]

    # 시설면적 필터링
    if area_size and "전체" not in area_size:
        filtered_df = filtered_df[filtered_df["시설면적_분류"].isin(area_size)]

    # 이용가능인원 필터링
    if capacity_size and "전체" not in capacity_size:
        filtered_df = filtered_df[filtered_df["이용가능인원_분류"].isin(capacity_size)]

    # 선풍기 필터링
    if has_fan_filter and "전체" not in has_fan_filter:
        filtered_df = filtered_df[filtered_df["선풍기_여부"].isin(has_fan_filter)]

    # 에어컨 필터링
    if has_ac_filter and "전체" not in has_ac_filter:
        filtered_df = filtered_df[filtered_df["에어컨_여부"].isin(has_ac_filter)]

    # 자치구 필터링
    if district and "전체" not in district:
        filtered_df = filtered_df[filtered_df["자치구"].isin(district)]

    return filtered_df


# 지도 생성 함수
def create_map(
    user_lat,
    user_lon,
    facility_type,
    area_size,
    capacity_size,
    has_fan_filter,
    has_ac_filter,
    district,
):
    """지도 생성 및 쉼터 표시"""
    df = load_data()
    df = preprocess_data(df)

    # 필터링 적용
    filtered_df = filter_data(
        df,
        facility_type,
        area_size,
        capacity_size,
        has_fan_filter,
        has_ac_filter,
        district,
    )

    # 지도 생성 (서울 중심)
    if user_lat and user_lon:
        center_lat, center_lon = user_lat, user_lon
    else:
        center_lat, center_lon = 37.5665, 126.9780  # 서울시청

    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    # 사용자 위치 표시
    if user_lat and user_lon:
        folium.Marker(
            [user_lat, user_lon],
            popup="내 위치",
            tooltip="내 위치",
            icon=folium.Icon(color="red", icon="user"),
        ).add_to(m)

    # 쉼터 마커 추가
    for idx, row in filtered_df.iterrows():
        if pd.notna(row["위도"]) and pd.notna(row["경도"]):
            popup_text = f"""
            <b>{row['쉼터명칭']}</b><br>
            시설구분: {row['시설구분2']}<br>
            주소: {row['도로명주소']}<br>
            면적: {row['시설면적']}㎡ ({row['시설면적_분류']})<br>
            수용인원: {row['이용가능인원']}명 ({row['이용가능인원_분류']})<br>
            선풍기: {row['선풍기_여부']}<br>
            에어컨: {row['에어컨_여부']}<br>
            야간운영: {row['야간운영여부']}<br>
            휴일운영: {row['휴일운영여부']}<br>
            숙박가능: {row['숙박가능여부']}
            """

            folium.Marker(
                [row["위도"], row["경도"]],
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=row["쉼터명칭"],
                icon=folium.Icon(color="blue", icon="home"),
            ).add_to(m)

    return m._repr_html_()


# 주변 쉼터 카드 생성
def get_nearby_shelters(
    user_lat,
    user_lon,
    facility_type,
    area_size,
    capacity_size,
    has_fan_filter,
    has_ac_filter,
    district,
):
    """주변 1km 내 쉼터 목록 반환"""
    if not user_lat or not user_lon:
        return "위치 정보를 입력해주세요."

    df = load_data()
    df = preprocess_data(df)

    # 필터링 적용
    filtered_df = filter_data(
        df,
        facility_type,
        area_size,
        capacity_size,
        has_fan_filter,
        has_ac_filter,
        district,
    )

    # 거리 계산 및 1km 이내 필터링
    nearby_shelters = []
    for idx, row in filtered_df.iterrows():
        if pd.notna(row["위도"]) and pd.notna(row["경도"]):
            distance = haversine(user_lon, user_lat, row["경도"], row["위도"])
            if distance <= 1.0:  # 1km 이내
                nearby_shelters.append(
                    {
                        "name": row["쉼터명칭"],
                        "type": row["시설구분2"],
                        "address": row["도로명주소"],
                        "area": f"{row['시설면적']}㎡ ({row['시설면적_분류']})",
                        "capacity": f"{row['이용가능인원']}명 ({row['이용가능인원_분류']})",
                        "fan": row["선풍기_여부"],
                        "ac": row["에어컨_여부"],
                        "night": row["야간운영여부"],
                        "holiday": row["휴일운영여부"],
                        "sleep": row["숙박가능여부"],
                        "distance": round(distance, 2),
                        "lat": row["위도"],
                        "lon": row["경도"],
                    }
                )

    # 거리순 정렬
    nearby_shelters.sort(key=lambda x: x["distance"])

    if not nearby_shelters:
        return "주변 1km 내에 조건에 맞는 쉼터가 없습니다."

    # HTML 카드 형태로 생성
    cards_html = "<div style='max-height: 600px; overflow-y: auto;'>"
    for shelter in nearby_shelters:
        # 카카오지도 길찾기 링크 생성
        kakao_directions_url = f"https://map.kakao.com/link/from/현재위치,{user_lat},{user_lon}/to/{shelter['name']},{shelter['lat']},{shelter['lon']}"

        cards_html += f"""
        <div style='border: 1px solid #ddd; margin: 10px; padding: 15px; border-radius: 8px; background-color: #f9f9f9;'>
            <h3 style='margin-top: 0; color: #2c3e50;'>{shelter['name']}</h3>
            <p><strong>거리:</strong> {shelter['distance']}km</p>
            <p><strong>시설구분:</strong> {shelter['type']}</p>
            <p><strong>주소:</strong> {shelter['address']}</p>
            <p><strong>면적:</strong> {shelter['area']}</p>
            <p><strong>수용인원:</strong> {shelter['capacity']}</p>
            <p><strong>편의시설:</strong> 선풍기 {shelter['fan']}, 에어컨 {shelter['ac']}</p>
            <p><strong>운영정보:</strong> 야간 {shelter['night']}, 휴일 {shelter['holiday']}, 숙박 {shelter['sleep']}</p>
            <div style='margin-top: 10px; text-align: center;'>
                <a href="{kakao_directions_url}" target="_blank" 
                   style='display: inline-block; padding: 8px 16px; background-color: #FEE500; color: #3C1E1E; 
                          text-decoration: none; border-radius: 4px; font-weight: bold; font-size: 14px;'>
                    🗺️ 카카오지도 길찾기
                </a>
            </div>
        </div>
        """
    cards_html += "</div>"

    return cards_html


# 위치 기반 자치구 추정 함수
def get_district_from_location(user_lat, user_lon):
    """사용자 위치 기반으로 자치구 추정"""
    if not user_lat or not user_lon:
        return "중구"  # 기본값

    df = load_data()
    df = preprocess_data(df)

    # 좌표가 있는 쉼터들만 필터링
    valid_shelters = df.dropna(subset=["위도", "경도"])

    if valid_shelters.empty:
        return "중구"

    # 모든 쉼터와의 거리 계산
    distances = []
    for idx, row in valid_shelters.iterrows():
        distance = haversine(user_lon, user_lat, row["경도"], row["위도"])
        distances.append({"distance": distance, "district": row["자치구"]})

    # 거리순 정렬
    distances.sort(key=lambda x: x["distance"])

    # 가장 가까운 5개 쉼터의 자치구 중 가장 많이 나오는 자치구 선택
    top_5_districts = [d["district"] for d in distances[:5] if d["district"] != "기타"]

    if top_5_districts:
        # 가장 많이 나오는 자치구 찾기
        from collections import Counter

        district_counts = Counter(top_5_districts)
        most_common_district = district_counts.most_common(1)[0][0]
        return most_common_district

    return "중구"  # 기본값


# 위치 정보 처리 함수 (자치구 자동 설정 포함)
def process_location_json(location_json):
    """JavaScript에서 받은 JSON 위치 정보를 처리하고 자치구도 자동 설정"""
    if not location_json:
        return None, None, None, "위치 정보를 가져올 수 없습니다."

    try:
        location = json.loads(location_json)

        if "error" in location:
            return None, None, None, f"오류: {location['error']}"

        latitude = location.get("latitude")
        longitude = location.get("longitude")
        accuracy = location.get("accuracy")

        if latitude is not None and longitude is not None:
            # 자치구 자동 감지
            detected_district = get_district_from_location(latitude, longitude)

            status_msg = f"위치를 성공적으로 가져왔습니다! (정확도: {accuracy:.0f}m)\n감지된 자치구: {detected_district}"
            return latitude, longitude, detected_district, status_msg
        else:
            return None, None, None, "위치 정보가 올바르지 않습니다."

    except Exception as e:
        return None, None, None, f"JSON 처리 중 오류: {str(e)}"


# 필터 옵션들을 가져오는 함수
def get_filter_options():
    """필터 드롭다운에 사용할 옵션들을 반환"""
    df = load_data()
    df = preprocess_data(df)

    # 필터 옵션들
    facility_types = ["전체"] + sorted(df["시설구분2"].dropna().unique().tolist())
    area_sizes = ["전체", "매우 작음", "작음", "보통", "큼", "매우 큼"]
    capacity_sizes = ["전체", "매우 적음", "적음", "보통", "많음", "매우 많음"]
    fan_options = ["전체", "있음", "없음"]
    ac_options = ["전체", "있음", "없음"]
    districts = ["전체"] + sorted(df["자치구"].dropna().unique().tolist())

    return {
        "facility_types": facility_types,
        "area_sizes": area_sizes,
        "capacity_sizes": capacity_sizes,
        "fan_options": fan_options,
        "ac_options": ac_options,
        "districts": districts,
    }
