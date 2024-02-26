let miniSearch = new MiniSearch({
  fields: ['title', 'par'], // fields to index for full-text search
  storeFields: ['title', 'par'], // fields to return with search results,
  idField: 'id',
  searchOptions: {
    boost: { 'par': 2 },
    fuzzy: false
  }
})


   
var all_chars_url = "https://raw.githubusercontent.com/catmus-guidelines/future-website/main/json/index.json"
let itemsById = {}
fetch(all_chars_url)
  .then(response => response.json())
  .then((allItems) => {
    itemsById = allItems.reduce((byId, item) => {
      byId[item.id] = item
      return byId
    }, {})
    console.log(allItems)
    return miniSearch.addAll(allItems)
  }).then(() => {
  })

  

// Index all documents


// Search with default options
// => [
//   { id: 2, title: 'Zen and the Art of Motorcycle Maintenance', category: 'fiction', score: 2.77258, match: { ... } },
//   { id: 4, title: 'Zen and the Art of Archery', category: 'non-fiction', score: 1.38629, match: { ... } }
// ]


$(function() {
    $("#search_symbol").click(function() {
    console.log("Initiating search")
    input_value = document.getElementById("search_input_guidelines").value;
    let results = miniSearch.search(input_value)
    for (result  of results) {
        console.log(result['title']);
        console.log(result);
}
    });
});