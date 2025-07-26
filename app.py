import gradio as gr
from utils import (
    create_map,
    get_nearby_shelters,
    process_location_json,
    get_filter_options,
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
