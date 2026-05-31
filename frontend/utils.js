const protocol = window.location.protocol;
const api = protocol + "//" + window.location.hostname + "/api";
const frontend = protocol + "//" + window.location.hostname;
const ws =
    (protocol === "https:" ? "wss:" : "ws:") +
    "//" +
    window.location.hostname +
    "/api";

function get_element(id) {
    return document.getElementById(id);
}

function request_json(path, method, body, on_success, on_error) {
    const options = {
        method: method,
        headers: { "Content-Type": "application/json" },
        credentials: "include",
    };

    if (body && method !== "GET") {
        options.body = JSON.stringify(body);
    }

    fetch(api + path, options)
        .then((response) => {
            if (!response.ok)
                throw new Error(`${response.status} ${response.statusText}`);

            const is_json = response.headers
                .get("content-type")
                ?.includes("application/json");
            return is_json ? response.json() : response.text();
        })
        .then((response) => {
            if (on_success) on_success(response);
        })
        .catch((error) => {
            if (on_error) on_error(error);
            else console.error(error);
        });
}

function redirect(path) {
    window.location.href = frontend + path;
}

function load_preset(name) {
    return frontend + "/presets/" + name;
}

document.documentElement.setAttribute("color-scheme", "dark");
