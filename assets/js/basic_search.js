let miniSearch = new MiniSearch({
  fields: ['title', 'text'], // fields to index for full-text search
  storeFields: ['title', 'category', 'id'] // fields to return with search results
})


   
var url = "https://raw.githubusercontent.com/catmus-guidelines/future-website/main/assets/js/albums.json"

var dataJson = {};
fetch(url)
  .then(response => response.text())
  .then((data) => {
    console.log(data)
    dataJson = data
    miniSearch.addAll(data)
  })
  

// Index all documents


// Search with default options
// => [
//   { id: 2, title: 'Zen and the Art of Motorcycle Maintenance', category: 'fiction', score: 2.77258, match: { ... } },
//   { id: 4, title: 'Zen and the Art of Archery', category: 'non-fiction', score: 1.38629, match: { ... } }
// ]


$(function() {
    $("#search_symbol").click(function() {
    input_value = document.getElementById("search_input_characters").value;
    let results = miniSearch.search(input_value)
    console.log(results)
    });
});