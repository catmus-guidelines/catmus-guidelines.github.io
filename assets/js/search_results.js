(function() {
            var results = JSON.parse(sessionStorage.getItem('myArray'))
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
                innerP.innerHTML = result['node'];
                innerDiv.append(innerP);
            }
        })();
