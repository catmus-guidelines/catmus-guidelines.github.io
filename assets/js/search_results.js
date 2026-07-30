/* Renders the results stashed by basic_search.js on /search.html. */

(function () {
   const main = document.getElementById('main');
   if (!main) {
      return;
   }

   let results = [];
   try {
      results = JSON.parse(sessionStorage.getItem('catmus_results')) || [];
   } catch (error) {
      results = [];
   }
   const query = sessionStorage.getItem('catmus_query') || '';

   const heading = document.createElement('p');
   heading.className = 'search_summary';
   heading.textContent = query
      ? results.length + ' result' + (results.length === 1 ? '' : 's') + ' for “' + query + '”'
      : 'No search query.';
   main.appendChild(heading);

   const container = document.createElement('div');
   container.id = 'div_result';
   main.appendChild(container);

   results.forEach(function (result) {
      const item = document.createElement('div');
      item.className = 'search_result';

      const title = document.createElement('span');
      title.className = 'spanResult';
      const link = document.createElement('a');
      link.href = result.url + (result.anchor ? '#' + result.anchor : '');
      link.textContent = result.title;
      title.appendChild(link);
      item.appendChild(title);

      const snippet = document.createElement('p');
      highlight(snippet, result.node, query);
      item.appendChild(snippet);

      container.appendChild(item);
   });

   /* Highlights every match, case-insensitively, using text nodes so that
      indexed content can never inject markup into this page. */
   function highlight(target, text, needle) {
      if (!needle) {
         target.textContent = text;
         return;
      }
      const pattern = new RegExp('(' + needle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
      let cursor = 0;
      text.replace(pattern, function (match, _group, offset) {
         target.appendChild(document.createTextNode(text.slice(cursor, offset)));
         const mark = document.createElement('span');
         mark.className = 'highlight';
         mark.textContent = match;
         target.appendChild(mark);
         cursor = offset + match.length;
         return match;
      });
      target.appendChild(document.createTextNode(text.slice(cursor)));
   }
})();
