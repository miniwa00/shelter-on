import gradio as gr
from utils import (
    create_map,
    get_nearby_shelters,
    process_location_json,
    get_filter_options,
    get_recommended_shelter,
)
from config import (
    GET_LOCATION_JS,
    APP_CONFIG,
    UI_TEXT,
    DEFAULT_COORDINATES,
    FILTER_LABELS,
)


# 위치 정보 처리 함수 (Gradio update 반환용 래퍼)
def process_location_json_for_gradio(location_json):
    """utils의 process_location_json을 감싸서 Gradio update 객체 반환"""
    latitude, longitude, detected_district, status_msg = process_location_json(
        location_json
    )

    if latitude is None:
        return gr.update(), gr.update(), gr.update(), status_msg
    else:
        # detected_district를 리스트로 변환 (멀티 선택을 위해)
        return latitude, longitude, [detected_district], status_msg


# Gradio 인터페이스 구성
def create_interface():
    # 필터 옵션들 가져오기
    filter_options = get_filter_options()

    facility_types = filter_options["facility_types"]
    area_sizes = filter_options["area_sizes"]
    capacity_sizes = filter_options["capacity_sizes"]
    fan_options = filter_options["fan_options"]
    ac_options = filter_options["ac_options"]
    districts = filter_options["districts"]

    with gr.Blocks(title=APP_CONFIG["title"], theme=gr.themes.Soft()) as demo:
        gr.Markdown(UI_TEXT["main_title"])

        # 위도, 경도를 숨겨진 상태로 관리
        user_lat = gr.State(value=DEFAULT_COORDINATES["latitude"])
        user_lon = gr.State(value=DEFAULT_COORDINATES["longitude"])

        with gr.Row():
            with gr.Column(scale=3):
                gr.Markdown(UI_TEXT["map_section"])
                map_html = gr.HTML()

            with gr.Column(scale=1):
                gr.Markdown(UI_TEXT["nearby_section"])
                nearby_list = gr.HTML()

        # 개인 맞춤 추천 섹션
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 👤 맞춤 추천 설정")
                is_elderly = gr.Checkbox(
                    label="65세 이상",
                    info="체크하면 경로당을 포함한 맞춤 쉼터를 추천합니다",
                )
                recommend_btn = gr.Button(
                    "🎯 맞춤 쉼터 추천받기", variant="primary", size="sm"
                )

            with gr.Column(scale=3):
                gr.Markdown("### 🎯 맞춤 쉼터 추천")
                recommendation_text = gr.Textbox(
                    show_label=False,
                    placeholder="65세 이상 여부를 선택하고 추천 버튼을 눌러주세요",
                    lines=2,
                    interactive=False,
                )
                recommendation_directions_btn = gr.HTML(value="", visible=False)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown(UI_TEXT["location_section"])
                gr.Markdown(UI_TEXT["location_guide"])

                with gr.Column(scale=1):
                    get_location_btn = gr.Button(
                        UI_TEXT["get_location_btn"], variant="secondary"
                    )
                    location_status = gr.Textbox(
                        label="위치 상태",
                        value=UI_TEXT["location_status_default"],
                        interactive=False,
                        lines=2,
                    )

                # 디버깅용 숨겨진 텍스트박스
                location_json_debug = gr.Textbox(
                    label="위치 JSON (디버깅)", visible=False
                )

            with gr.Column(scale=3):
                gr.Markdown(UI_TEXT["filter_section"])
                with gr.Row():
                    facility_type = gr.Dropdown(
                        choices=facility_types,
                        label=FILTER_LABELS["facility_type"],
                        value=["전체"],
                        multiselect=True,
                    )
                    area_size = gr.Dropdown(
                        choices=area_sizes,
                        label=FILTER_LABELS["area_size"],
                        value=["전체"],
                        multiselect=True,
                    )
                    capacity_size = gr.Dropdown(
                        choices=capacity_sizes,
                        label=FILTER_LABELS["capacity_size"],
                        value=["전체"],
                        multiselect=True,
                    )
                with gr.Row():
                    has_fan_filter = gr.Dropdown(
                        choices=fan_options,
                        label=FILTER_LABELS["fan_filter"],
                        value=["전체"],
                        multiselect=True,
                    )
                    has_ac_filter = gr.Dropdown(
                        choices=ac_options,
                        label=FILTER_LABELS["ac_filter"],
                        value=["전체"],
                        multiselect=True,
                    )
                    # 자치구 필터 (자동 설정됨)
                    district = gr.Dropdown(
                        choices=districts,
                        label=FILTER_LABELS["district"],
                        value=["중구"],
                        multiselect=True,
                    )

                update_btn = gr.Button(
                    UI_TEXT["update_btn"], variant="primary", size="sm", visible=False
                )

        # 이벤트 핸들러
        def update_all(lat, lon, f_type, a_size, c_size, fan_filter, ac_filter, dist):
            map_result = create_map(
                lat, lon, f_type, a_size, c_size, fan_filter, ac_filter, dist
            )
            nearby_result = get_nearby_shelters(
                lat, lon, f_type, a_size, c_size, fan_filter, ac_filter, dist
            )
            return map_result, nearby_result

        # 위치 가져오기 버튼
        get_location_btn.click(
            None,
            js=GET_LOCATION_JS,
            outputs=[location_json_debug],
        )

        # 위치 JSON이 업데이트되면 각 컴포넌트에 값 전달 (자치구 포함)
        location_json_debug.change(
            fn=process_location_json_for_gradio,
            inputs=[location_json_debug],
            outputs=[user_lat, user_lon, district, location_status],  # district 추가
        )

        # 지도 업데이트 버튼 이벤트
        update_btn.click(
            fn=update_all,
            inputs=[
                user_lat,
                user_lon,
                facility_type,
                area_size,
                capacity_size,
                has_fan_filter,
                has_ac_filter,
                district,
            ],
            outputs=[map_html, nearby_list],
        )

        # 추천 버튼 이벤트 핸들러
        def get_recommendation(lat, lon, is_elderly):
            # 65세 이상 여부에 따라 나이 설정
            user_age = 65 if is_elderly else 25  # 65세 이상이면 65, 아니면 25
            user_name = "사용자"  # 기본 이름

            recommendation_text, shelter_name, shelter_lat, shelter_lon = (
                get_recommended_shelter(lat, lon, user_age, user_name)
            )

            if shelter_name and shelter_lat and shelter_lon:
                # 카카오지도 길찾기 링크 생성
                kakao_directions_url = f"https://map.kakao.com/link/from/현재위치,{lat},{lon}/to/{shelter_name},{shelter_lat},{shelter_lon}"

                # 카드 섹션과 동일한 스타일의 버튼 HTML 생성 (중앙 정렬)
                button_html = f"""
                <div style='text-align: center; display: flex; justify-content: center;'>
                    <a href="{kakao_directions_url}" target="_blank" 
                       style='display: inline-block; padding: 8px 16px; background-color: #FEE500; color: #3C1E1E; 
                              text-decoration: none; border-radius: 4px; font-weight: bold; font-size: 14px;'>
                        🗺️ 카카오지도 길찾기
                    </a>
                </div>
                """
                return recommendation_text, gr.update(visible=True, value=button_html)
            else:
                return recommendation_text, gr.update(visible=False)

        recommend_btn.click(
            fn=get_recommendation,
            inputs=[user_lat, user_lon, is_elderly],
            outputs=[recommendation_text, recommendation_directions_btn],
        )

        # 위치가 변경될 때 자동으로 지도 업데이트
        for component in [user_lat, user_lon]:
            component.change(
                fn=update_all,
                inputs=[
                    user_lat,
                    user_lon,
                    facility_type,
                    area_size,
                    capacity_size,
                    has_fan_filter,
                    has_ac_filter,
                    district,
                ],
                outputs=[map_html, nearby_list],
            )

        # 필터가 변경될 때 자동으로 지도 업데이트
        for filter_component in [
            facility_type,
            area_size,
            capacity_size,
            has_fan_filter,
            has_ac_filter,
            district,
        ]:
            filter_component.change(
                fn=update_all,
                inputs=[
                    user_lat,
                    user_lon,
                    facility_type,
                    area_size,
                    capacity_size,
                    has_fan_filter,
                    has_ac_filter,
                    district,
                ],
                outputs=[map_html, nearby_list],
            )

        # 수동 좌표 입력 아코디언
        with gr.Accordion("📍 수동 좌표 입력", open=False):
            gr.Markdown("위도와 경도를 직접 입력하여 위치를 설정할 수 있습니다.")
            with gr.Row():
                manual_lat = gr.Textbox(
                    label="위도", placeholder="예: 37.5665", lines=1
                )
                manual_lon = gr.Textbox(
                    label="경도", placeholder="예: 126.9780", lines=1
                )
            manual_location_btn = gr.Button(
                "📍 위치 설정", variant="secondary", size="sm"
            )

            gr.Markdown("### 🏛️ 테스트용 랜드마크")
            gr.Markdown("아래 랜드마크를 클릭하면 해당 위치로 자동 설정됩니다.")

            # 서울 주요 랜드마크들
            landmarks = [
                ("🏛️ 서울시청", 37.5665, 126.9780),
                ("🗼 남산타워", 37.5512, 126.9882),
                ("🏰 경복궁", 37.5796, 126.9770),
                ("🏛️ 광화문", 37.5725, 126.9769),
                ("🏢 강남역", 37.4980, 127.0276),
                ("🏢 홍대입구역", 37.5572, 126.9254),
                ("🏢 명동", 37.5636, 126.9834),
                ("🏢 동대문", 37.5714, 127.0095),
                ("🏢 잠실역", 37.5139, 127.1006),
                ("🏢 강남구청", 37.5172, 127.0473),
                ("🏢 서초구청", 37.4837, 127.0324),
                ("🏢 마포구청", 37.5637, 126.9084),
                ("🏢 종로구청", 37.5734, 126.9790),
                ("🏢 중구청", 37.5638, 126.9974),
            ]

            # 랜드마크 버튼들을 반반으로 나누어 배치
            with gr.Row():
                with gr.Column(scale=1):
                    landmark_buttons_left = []
                    for name, lat, lon in landmarks[:7]:  # 왼쪽 7개
                        btn = gr.Button(
                            name,
                            variant="outline",
                            size="sm",
                            elem_classes=["landmark-btn"],
                        )
                        landmark_buttons_left.append((btn, lat, lon))

                with gr.Column(scale=1):
                    landmark_buttons_right = []
                    for name, lat, lon in landmarks[7:]:  # 오른쪽 7개
                        btn = gr.Button(
                            name,
                            variant="outline",
                            size="sm",
                            elem_classes=["landmark-btn"],
                        )
                        landmark_buttons_right.append((btn, lat, lon))

            # 모든 랜드마크 버튼을 하나의 리스트로 합치기
            landmark_buttons = landmark_buttons_left + landmark_buttons_right

        # 수동 좌표 입력 이벤트 핸들러
        def set_manual_location(lat, lon):
            try:
                lat = float(lat)
                lon = float(lon)
                return lat, lon
            except (ValueError, TypeError):
                return None, None

        # 수동 좌표 입력 시 지도와 주변 쉼터 업데이트
        def set_manual_location_and_update(
            lat, lon, f_type, a_size, c_size, fan_filter, ac_filter, dist
        ):
            try:
                lat = float(lat)
                lon = float(lon)

                # 새로운 위치의 자치구 감지
                from utils import get_district_from_location

                detected_district = get_district_from_location(lat, lon)

                # 지도와 주변 쉼터 업데이트
                map_result = create_map(
                    lat,
                    lon,
                    f_type,
                    a_size,
                    c_size,
                    fan_filter,
                    ac_filter,
                    [detected_district],
                )
                nearby_result = get_nearby_shelters(
                    lat,
                    lon,
                    f_type,
                    a_size,
                    c_size,
                    fan_filter,
                    ac_filter,
                    [detected_district],
                )
                return lat, lon, map_result, nearby_result, [detected_district]
            except (ValueError, TypeError):
                return None, None, gr.update(), gr.update(), gr.update()

        manual_location_btn.click(
            fn=set_manual_location_and_update,
            inputs=[
                manual_lat,
                manual_lon,
                facility_type,
                area_size,
                capacity_size,
                has_fan_filter,
                has_ac_filter,
                district,
            ],
            outputs=[user_lat, user_lon, map_html, nearby_list, district],
        )

        # 랜드마크 버튼 클릭 이벤트
        def set_landmark_location(
            lat, lon, f_type, a_size, c_size, fan_filter, ac_filter, dist
        ):
            # 새로운 위치의 자치구 감지
            from utils import get_district_from_location

            detected_district = get_district_from_location(lat, lon)

            # 지도와 주변 쉼터 업데이트
            map_result = create_map(
                lat,
                lon,
                f_type,
                a_size,
                c_size,
                fan_filter,
                ac_filter,
                [detected_district],
            )
            nearby_result = get_nearby_shelters(
                lat,
                lon,
                f_type,
                a_size,
                c_size,
                fan_filter,
                ac_filter,
                [detected_district],
            )
            return lat, lon, map_result, nearby_result, [detected_district]

        # 각 랜드마크 버튼에 이벤트 연결
        for btn, lat, lon in landmark_buttons:
            btn.click(
                fn=set_landmark_location,
                inputs=[
                    gr.State(lat),
                    gr.State(lon),
                    facility_type,
                    area_size,
                    capacity_size,
                    has_fan_filter,
                    has_ac_filter,
                    district,
                ],
                outputs=[user_lat, user_lon, map_html, nearby_list, district],
            )

        # 초기 로드
        demo.load(
            fn=update_all,
            inputs=[
                user_lat,
                user_lon,
                facility_type,
                area_size,
                capacity_size,
                has_fan_filter,
                has_ac_filter,
                district,
            ],
            outputs=[map_html, nearby_list],
        )

    return demo


# 모듈 레벨에서 demo 생성
demo = create_interface()

if __name__ == "__main__":
    demo.launch(
        share=APP_CONFIG["share"],
        server_name=APP_CONFIG["server_name"],
        server_port=APP_CONFIG["server_port"],
    )
