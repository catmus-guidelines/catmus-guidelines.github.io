/* Client-side search over json/index.json, built by scripts/index_site.py.
   Results are handed to search.html through sessionStorage. */

const miniSearch = new MiniSearch({
   fields: ['title', 'node'],
   storeFields: ['title', 'node', 'url', 'anchor'],
   idField: 'id',
   searchOptions: {
      boost: { node: 2 },
      prefix: true,
      fuzzy: 0.15
   }
});

let indexReady = fetch('/json/index.json')
   .then((response) => {
      if (!response.ok) {
         throw new Error('index.json returned ' + response.status);
      }
      return response.json();
   })
   .then((items) => miniSearch.addAll(items))
   .catch((error) => console.error('search index unavailable:', error));

const form = document.getElementById('search');
if (form) {
   form.addEventListener('submit', function (event) {
      event.preventDefault();
      const query = document.getElementById('search_input_guidelines').value.trim();
      if (!query) {
         return;
      }
      // The index may still be loading on a fast submit, so wait on it rather
      // than searching an empty index and reporting no results.
      indexReady.then(() => {
         const results = miniSearch.search(query).slice(0, 100).map((result) => ({
            title: result.title,
            url: result.url,
            // `anchor` is the id stamped onto the indexed block; the previous
            // version used the record id, which is not an element id at all, so
            // every result link landed at the top of the page.
            anchor: result.anchor,
            node: result.node
         }));
         sessionStorage.setItem('catmus_results', JSON.stringify(results));
         sessionStorage.setItem('catmus_query', query);
         window.location.assign('/search.html');
      });
   });
}
