function highlight(chars, to_find){
    var tokenized = chars.split(' ')
    var tokenized_search = to_find.split(' ')
    var out_string = chars.replace(" " + to_find + " ", "<span class='highlight'>" + to_find + '</span>')
    console.log(out_string)
    var highlighted_string = out_string
    return highlighted_string
};

(function() {
        var results = JSON.parse(sessionStorage.getItem('myArray'))
        var search = sessionStorage.getItem('search_string')
        console.log(search)
            console.log(results)
            newDiv = document.createElement("div")
            newDiv.setAttribute("id", "div_result")
            main_node = document.getElementById("main")
            main_node.appendChild(newDiv);
            for (result of results) {
                console.log(result);
                innerDiv = document.createElement("div");
                head = document.createElement("span");
                head.setAttribute("class", "spanResult")
                link = document.createElement("a");
                link.setAttribute("href", result['url'] + "#" + result['id'])
                link.innerHTML = result['title'];
                head.append(link)
                divResult = document.getElementById("div_result")
                divResult.appendChild(innerDiv);
                innerDiv.append(head);
                innerP = document.createElement("p");
                highlighted_node = highlight(result['node'], search);
                innerP.innerHTML = highlighted_node;
                innerDiv.append(innerP);
            }
        })();



