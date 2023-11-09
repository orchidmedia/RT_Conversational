import json
import os

import ipyleaflet
from openai import OpenAI, NotFoundError
from openai.types.beta import Thread

import time

import solara

center_default = (0, 0)
zoom_default = 2

messages = solara.reactive([])
zoom_level = solara.reactive(zoom_default)
center = solara.reactive(center_default)
markers = solara.reactive([])

url = ipyleaflet.basemaps.OpenStreetMap.Mapnik.build_url()
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model = "gpt-4-1106-preview"


# Declare tools for openai assistant to use
tools = [
    {
        "type": "function",
        "function": {
            "name": "update_map",
            "description": "Update map to center on a particular location",
            "parameters": {
                "type": "object",
                "properties": {
                    "longitude": {
                        "type": "number",
                        "description": "Longitude of the location to center the map on",
                    },
                    "latitude": {
                        "type": "number",
                        "description": "Latitude of the location to center the map on",
                    },
                    "zoom": {
                        "type": "integer",
                        "description": "Zoom level of the map",
                    },
                },
                "required": ["longitude", "latitude", "zoom"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_marker",
            "description": "Add marker to the map",
            "parameters": {
                "type": "object",
                "properties": {
                    "longitude": {
                        "type": "number",
                        "description": "Longitude of the location to the marker",
                    },
                    "latitude": {
                        "type": "number",
                        "description": "Latitude of the location to the marker",
                    },
                    "label": {
                        "type": "string",
                        "description": "Text to display on the marker",
                    },
                },
                "required": ["longitude", "latitude", "label"],
            },
        },
    },
]


def update_map(longitude, latitude, zoom):
    center.set((latitude, longitude))
    zoom_level.set(zoom)
    return "Map updated"


def add_marker(longitude, latitude, label):
    markers.set(markers.value + [{"location": (latitude, longitude), "label": label}])
    return "Marker added"


functions = {
    "update_map": update_map,
    "add_marker": add_marker,
}


def ai_call(tool_call):
    function = tool_call.function
    name = function.name
    arguments = json.loads(function.arguments)
    return_value = functions[name](**arguments)
    tool_outputs = {
        "tool_call_id": tool_call.id,
        "output": return_value,
    }
    return tool_outputs


@solara.component
def Map():
    ipyleaflet.Map.element(  # type: ignore
        zoom=zoom_level.value,
        center=center.value,
        scroll_wheel_zoom=True,
        layers=[
            ipyleaflet.TileLayer.element(url=url),
            *[
                ipyleaflet.Marker.element(location=k["location"], draggable=False)
                for k in markers.value
            ],
        ],
    )


@solara.component
def ChatInterface():
    prompt = solara.use_reactive("")
    run_id: solara.Reactive[str] = solara.use_reactive(None)

    thread: Thread = solara.use_memo(openai.beta.threads.create, dependencies=[])

    def add_message(value: str):
        if value == "":
            return
        prompt.set("")
        new_message = openai.beta.threads.messages.create(
            thread_id=thread.id, content=value, role="user"
        )
        messages.set([*messages.value, new_message])
        run_id.value = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id="asst_RqVKAzaybZ8un7chIwPCIQdH",
            tools=tools,
        ).id

    def poll():
        if not run_id.value:
            return
        completed = False
        while not completed:
            try:
                run = openai.beta.threads.runs.retrieve(
                    run_id.value, thread_id=thread.id
                )
            # Above will raise NotFoundError when run creation is still in progress
            except NotFoundError:
                continue
            if run.status == "requires_action":
                tool_outputs = []
                for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    tool_output = ai_call(tool_call)
                    tool_outputs.append(tool_output)
                    messages.set([*messages.value, tool_output])
                openai.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread.id,
                    run_id=run_id.value,
                    tool_outputs=tool_outputs,
                )
            if run.status == "completed":
                messages.set(
                    [
                        *messages.value,
                        openai.beta.threads.messages.list(thread.id).data[0],
                    ]
                )
                run_id.set(None)
                completed = True
            time.sleep(0.1)

    result = solara.use_thread(poll, dependencies=[run_id.value])

    # Create DOM for chat interface
    with solara.Column(
        classes=["chat-interface"],
    ):
        if len(messages.value) > 0:
            # The height works effectively as `min-height`, since flex will grow the container to fill the available space
            with solara.Column(
                style={
                    "flex-grow": "1",
                    "overflow-y": "auto",
                    "height": "100px",
                    "flex-direction": "column-reverse",
                },
                classes=["chat-box"],
            ):
                for message in reversed(messages.value):
                    with solara.Row(style={"align-items": "flex-start"}):
                        # Catch "messages" that are actually tool calls
                        if isinstance(message, dict):
                            icon = (
                                "mdi-map"
                                if message["output"] == "Map updated"
                                else "mdi-map-marker"
                            )
                            solara.v.Icon(children=[icon], style_="padding-top: 10px;")
                            solara.Markdown(message["output"])
                        elif message.role == "user":
                            solara.Text(
                                message.content[0].text.value,
                                classes=["chat-message", "user-message"],
                            )
                        elif message.role == "assistant":
                            if message.content[0].text.value:
                                solara.v.Icon(
                                    children=["mdi-compass-outline"],
                                    style_="padding-top: 10px;",
                                )
                                solara.Markdown(message.content[0].text.value)
                            elif message.content.tool_calls:
                                solara.v.Icon(
                                    children=["mdi-map"],
                                    style_="padding-top: 10px;",
                                )
                                solara.Markdown("*Calling map functions*")
                            else:
                                solara.v.Icon(
                                    children=["mdi-compass-outline"],
                                    style_="padding-top: 10px;",
                                )
                                solara.Preformatted(
                                    repr(message),
                                    classes=["chat-message", "assistant-message"],
                                )
                        else:
                            solara.v.Icon(
                                children=["mdi-compass-outline"],
                                style_="padding-top: 10px;",
                            )
                            solara.Preformatted(
                                repr(message),
                                classes=["chat-message", "assistant-message"],
                            )
        with solara.Column():
            solara.InputText(
                label="Ask your question here",
                value=prompt,
                style={"flex-grow": "1"},
                on_value=add_message,
                disabled=result.state == solara.ResultState.RUNNING,
            )
            solara.ProgressLinear(result.state == solara.ResultState.RUNNING)
            if result.state == solara.ResultState.ERROR:
                solara.Error(repr(result.error))


@solara.component
def Page():
    with solara.Column(
        classes=["ui-container"],
        gap="5vh",
    ):
        with solara.Row(justify="space-between"):
            with solara.Row(gap="10px", style={"align-items": "center"}):
                solara.v.Icon(children=["mdi-compass-rose"], size="36px")
                solara.HTML(
                    tag="h2",
                    unsafe_innerHTML="Orchid Media",
                    style={"display": "inline-block"},
                )
        with solara.Row(
            justify="space-between", style={"flex-grow": "1"}, classes=["container-row"]
        ):
            ChatInterface()
            with solara.Column(classes=["map-container"]):
                Map()

        solara.Style(
            """
            .jupyter-widgets.leaflet-widgets{
                height: 100%;
                border-radius: 20px;
            }
            .solara-autorouter-content{
                display: flex;
                flex-direction: column;
                justify-content: stretch;
            }
            .v-toolbar__title{
                display: flex;
                align-items: center;
                column-gap: 0.5rem;
            }
            .ui-container{
                height: 95vh;
                justify-content: center;
                padding: 45px 50px 75px 50px;
            }
            .chat-interface{
                height: 100%;
                width: 38vw;
                justify-content: center;
                position: relative;
            }
            .chat-interface:after {
                content: "";
                position: absolute;
                z-index: 1;
                top: 0;
                left: 0;
                pointer-events: none;
                background-image: linear-gradient(to top, rgba(255,255,255,0), rgba(255,255,255, 1) 100%);
                width: 100%;
                height: 15%;
            }
            .chat-box > :last-child{
                padding-top: 7.5vh;
            }
            .map-container{
                width: 50vw;
                height: 100%;
                justify-content: center;
            }
            .user-message{
                font-weight: bold;
            }
            @media screen and (max-aspect-ratio: 1/1) {
                .ui-container{
                    padding: 30px;
                    height: 100vh;
                }
                .container-row{
                    flex-direction: column-reverse !important;
                    width: 100% !important;
                }
                .chat-interface{
                    width: unset;
                    justify-content: flex-end;
                }
                .map-container{
                    width: unset;
                }
            }
            """
        )
