let miniSearch = new MiniSearch({
  fields: ['title', 'node', 'url'], // fields to index for full-text search
  storeFields: ['title', 'node', 'url'], // fields to return with search results,
  idField: 'id',
  searchOptions: {
    boost: { 'node': 2 },
    fuzzy: false
  }
})


   
function fetch_json() {
var all_chars_url = url + "/json/index.json"
let itemsById = {}
fetch(all_chars_url)
  .then(response => response.json())
  .then((allItems) => {
    itemsById = allItems.reduce((byId, item) => {
      byId[item.id] = item
      return byId
    }, {})
    console.log(allItems);
    return miniSearch.addAll(allItems)
  }).then(() => {
  })
}
  

// Index all documents


// Search with default options
// => [
//   { id: 2, title: 'Zen and the Art of Motorcycle Maintenance', category: 'fiction', score: 2.77258, match: { ... } },
//   { id: 4, title: 'Zen and the Art of Archery', category: 'non-fiction', score: 1.38629, match: { ... } }
// ]


const head = document.head
console.log(head)
const url = head.getAttribute("about");

fetch_json();
document.getElementById("search").addEventListener("submit", function (event) {
event.preventDefault();
console.log("Initiating search")
input_value = document.getElementById("search_input_guidelines").value;
let results = miniSearch.search(input_value)
var myList = []
for (result  of results) {
    var myDict = {}
    myDict['title'] = result['title']
    myDict['url'] = result['url']
    myDict['node'] = result['node']
    myDict['id'] = result['id']
    myList.push(myDict)
}
sessionStorage.setItem('myArray', JSON.stringify(myList));
sessionStorage.setItem('search_string', input_value);
window.location.replace(url + "/search.html");
});



