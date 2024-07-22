## Semantic segmentation, with some exceptions

The term segmentation is ambiguous and can refer to several phases of automated text processing. Here, by segmentation we mean the **separation of text into "words"**. 

Distinguishing between the presence or absence of a typographic space is sometimes purely subjective, as this notion only really makes sense for printed matter. 
<!-- AC:I think this is too convoluted here, since they are guidelines, it needs to be more straight forward--> 
<!--However, while we are aware that practice will always be heterogeneous and involve an element of arbitrariness, we advocate a practice based on the meaning of the text, separating semantic words wherever possible. -->
To simplify decision making, we suggest following the meaning of the text, separating semantic words wherever possible.

To ensure homogeneity, the separation of words should follow a modernized segmentation, even if this does not prevent some ambiguities. 

There is one exception to this principle. When modern usage would like to show an elision, whereas the **medieval manuscript** tends to use an agglutination, the agglutination is retained. When in doubt about the segmentation of words in the manuscript, we recommend adopting a segmentation that conforms to that of the contemporary language of the manuscript. 

Some cases may be more difficult to decide, notably for verbs such as "enchargier", "en fuir", "en partir" or certain locutions. Try to stay as close as possible to the source, and in case of doubt, follow either the dictionary entry or modern usage. For example, for modern documents in French, if the segmented form presented in the source exists in the [DMF](http://zeus.atilf.fr/dmf/), we should keep the segmented form.

Following the same principle, in the case of cursive writing, agglutinations and dragging strokes should not be imitated, thus one would transcribe "et en effet" and not "eteneffet" or "et_en_effet".


## Respecting hyphenation when it exists

Hyphenation is the act of indicating that a word has been cut off at the end of the line; it is a practice that appears in a number of medieval manuscripts, although it is not a general rule. It is much more common in modern and contemporary documents.

Hyphenation should be retained **when it appears in the source document**, and should not be added if no sign is present on the page. The character "-" [U+002D] is the character used by the CATMuS project, whichever symbol is used on the source document.

<!-- AC: initially for the modern guidelines, we said we would distinguish between césure and trait-d'union, using - for the former and ¬ for the latter. Upon reading the medieval guidelines, I think the modern guidelines should stick to the same rule and use only -, especially since "trait-d'union" also translates into "hyphen" -->

<!-- AC: I don't know if this should be a rule only for Modern documents or if it is also applicable to medieval docs -->
When the hyphenation symbol is repeated at the beginning of the next line, it should also be transcribed with "-" [U+002D].

## Diastoles

Sometimes, diastoles (vertical or oblique pen strokes) are drawn between two contiguous letters to indicate that they belong to different words. We recommend transcribing them with the following sign: "/" [U+002F].

In **modern documents**, for the oldest ones, diastoles may be transcribed with "/" [U+002F] or "," [(U+002C], depending on the sign used in the source document. Otherwise, oblique strokes should always be transcribed with "/".
