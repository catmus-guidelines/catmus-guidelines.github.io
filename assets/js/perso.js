$(document).ready(function() {
    var current_url = getCurrentURL();
    current_lang = current_url.split("/").at(-2);
    console.log(current_lang);
    if (current_lang == "en" || current_url.includes("-en")) {
        document.getElementById("language").innerHTML = "Version française";
    } else {
        document.getElementById("language").innerHTML = "English version";
    }
});


function getCurrentURL() {
    return window.location.href
}

$(function() {
    $("#language").click(function() {
        var current_url = getCurrentURL();
        current_lang = current_url.split("/").at(-2);
        console.log(current_lang);
        if (current_lang == "fr" || current_lang == "en") {
            if (current_lang == "en") {
                other_lang = "fr"
            } else {
                other_lang = "en"
            }
        console.log(other_lang)
        orig_string = "/" + current_lang + "/";
        replacement_string = "/" + other_lang + "/";
        target_url = current_url.replace(orig_string, replacement_string);
        console.log(target_url);
        window.location.replace(target_url);
        } else {
            index_version = current_url.split("/").at(-1)
            console.log(index_version)
            if (index_version.includes("en")) {
            target_url = current_url.replace("-en", "")
            } else {
            target_url = current_url.replace(".html", "-en.html")
            }
        window.location.replace(target_url);
        }
    });
});