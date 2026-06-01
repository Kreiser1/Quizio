const protocol = window.location.protocol;
const api = protocol + "//" + window.location.hostname + "/api";
const frontend = protocol + "//" + window.location.hostname;
const ws =
    (protocol === "https:" ? "wss:" : "ws:") +
    "//" +
    window.location.hostname +
    "/api";

document.documentElement.setAttribute("color-scheme", "dark");

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

function request_download(path, method, body, filename, on_error) {
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
            return response.blob();
        })
        .then((blob) => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
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

const AuthAPI = {
    register: (data, on_success, on_error) => {
        request_json("/auth/register", "POST", data, on_success, on_error);
    },

    login: (data, on_success, on_error) => {
        request_json("/auth/login", "POST", data, on_success, on_error);
    },

    logout: (refresh_token, on_success, on_error) => {
        const body = refresh_token ? { refresh_token: refresh_token } : {};
        request_json("/auth/logout", "POST", body, on_success, on_error);
    },

    update_credentials: (data, on_success, on_error) => {
        request_json("/auth/register", "PATCH", data, on_success, on_error);
    },

    getSessions: (on_success, on_error) => {
        request_json("/auth/sessions", "GET", null, on_success, on_error);
    },
};

const UsersAPI = {
    get_profile: (on_success, on_error) => {
        request_json("/users/me", "GET", null, on_success, on_error);
    },

    update_profile: (data, on_success, on_error) => {
        request_json("/users/me", "PATCH", data, on_success, on_error);
    },

    get_user_profile: (username, on_success, on_error) => {
        request_json(
            `/users/${encodeURIComponent(username)}`,
            "GET",
            null,
            on_success,
            on_error,
        );
    },
};

const AdminAPI = {
    get_users: (on_success, on_error) => {
        request_json("/admin/users", "GET", null, on_success, on_error);
    },

    update_role: (data, on_success, on_error) => {
        request_json(
            `/admin/users/${encodeURIComponent(data.username)}/role`,
            "PATCH",
            data,
            on_success,
            on_error,
        );
    },

    update_credentials: (username, data, on_success, on_error) => {
        request_json(
            `/admin/users/${encodeURIComponent(username)}/credentials`,
            "PATCH",
            data,
            on_success,
            on_error,
        );
    },

    update_profile: (username, data, on_success, on_error) => {
        request_json(
            `/admin/users/${encodeURIComponent(username)}`,
            "PATCH",
            data,
            on_success,
            on_error,
        );
    },

    delete_user: (username, on_success, on_error) => {
        request_json(
            `/admin/users/${encodeURIComponent(username)}`,
            "DELETE",
            null,
            on_success,
            on_error,
        );
    },
};

const QuizzesAPI = {
    create: (data, on_success, on_error) => {
        request_json("/quizzes", "POST", data, on_success, on_error);
    },

    search: (params, on_success, on_error) => {
        const queryParams = new URLSearchParams();
        if (params.query) queryParams.append("query", params.query);
        if (params.tags)
            params.tags.forEach((t) => queryParams.append("tags", t));
        if (params.count) queryParams.append("count", params.count);
        if (params.offset) queryParams.append("offset", params.offset);

        const url = `/quizzes/query${queryParams.toString() ? "?" + queryParams.toString() : ""}`;
        request_json(url, "GET", null, on_success, on_error);
    },

    get: (id, on_success, on_error) => {
        request_json(`/quizzes/${id}`, "GET", null, on_success, on_error);
    },

    update: (id, data, on_success, on_error) => {
        request_json(`/quizzes/${id}`, "PATCH", data, on_success, on_error);
    },

    delete: (id, on_success, on_error) => {
        request_json(`/quizzes/${id}`, "DELETE", null, on_success, on_error);
    },

    get_authors: (id, on_success, on_error) => {
        request_json(
            `/quizzes/${id}/authors`,
            "GET",
            null,
            on_success,
            on_error,
        );
    },

    add_author: (id, author, on_success, on_error) => {
        request_json(
            `/quizzes/${id}/authors`,
            "POST",
            { author: author },
            on_success,
            on_error,
        );
    },

    remove_author: (id, author, on_success, on_error) => {
        request_json(
            `/quizzes/${id}/authors/${encodeURIComponent(author)}`,
            "DELETE",
            null,
            on_success,
            on_error,
        );
    },

    download_yaml: (id, filename = `quiz_${id}.yaml`, on_error) => {
        request_download(
            `/quizzes/${id}/yaml`,
            "GET",
            null,
            filename,
            on_error,
        );
    },
};

const AchievementsAPI = {
    create: (data, on_success, on_error) => {
        request_json("/achievements", "POST", data, on_success, on_error);
    },

    delete: (id, on_success, on_error) => {
        request_json(
            `/achievements/${id}`,
            "DELETE",
            null,
            on_success,
            on_error,
        );
    },

    get_my_achievements: (on_success, on_error) => {
        request_json("/achievements", "GET", null, on_success, on_error);
    },

    get_all: (on_success, on_error) => {
        request_json("/achievements/all", "GET", null, on_success, on_error);
    },
};

const RoomsAPI = {
    create: (data, on_success, on_error) => {
        request_json("/rooms", "POST", data, on_success, on_error);
    },

    search: (params, on_success, on_error) => {
        const queryParams = new URLSearchParams();
        if (params.query) queryParams.append("query", params.query);
        if (params.count) queryParams.append("count", params.count);
        if (params.offset) queryParams.append("offset", params.offset);

        const url = `/rooms/query${queryParams.toString() ? "?" + queryParams.toString() : ""}`;
        request_json(url, "GET", null, on_success, on_error);
    },

    get: (room_token, on_success, on_error) => {
        request_json(`/rooms/${room_token}`, "GET", null, on_success, on_error);
    },

    submit_answer: (room_token, data, on_success, on_error) => {
        request_json(
            `/rooms/${room_token}/answer`,
            "POST",
            data,
            on_success,
            on_error,
        );
    },

    control: (room_token, data, on_success, on_error) => {
        request_json(
            `/rooms/${room_token}/control`,
            "POST",
            data,
            on_success,
            on_error,
        );
    },

    ban_user: (room_token, username, on_success, on_error) => {
        request_json(
            `/rooms/${room_token}/ban`,
            "POST",
            { username: username },
            on_success,
            on_error,
        );
    },

    unban_user: (room_token, username, on_success, on_error) => {
        request_json(
            `/rooms/${room_token}/unban`,
            "POST",
            { username: username },
            on_success,
            on_error,
        );
    },

    add_team: (room_token, data, on_success, on_error) => {
        request_json(
            `/rooms/${room_token}/teams`,
            "POST",
            data,
            on_success,
            on_error,
        );
    },

    delete_team: (room_token, title, on_success, on_error) => {
        request_json(
            `/rooms/${room_token}/teams`,
            "DELETE",
            { title: title },
            on_success,
            on_error,
        );
    },

    set_user_team: (room_token, username, title, on_success, on_error) => {
        request_json(
            `/rooms/${room_token}/team`,
            "POST",
            { username: username, title: title },
            on_success,
            on_error,
        );
    },

    connectStream: (room_token, callbacks) => {
        const ws_url = `${ws}/rooms/${room_token}/stream`;
        const socket = new WebSocket(ws_url);

        if (callbacks.onOpen) socket.onopen = callbacks.onOpen;
        if (callbacks.onClose) socket.onclose = callbacks.onClose;
        if (callbacks.onError) socket.onerror = callbacks.onError;
        if (callbacks.onMessage) {
            socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                callbacks.onMessage(data);
            };
        }

        return socket;
    },
};

function file_to_base64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () =>
            resolve(reader.result.split(",")[1] || reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}
