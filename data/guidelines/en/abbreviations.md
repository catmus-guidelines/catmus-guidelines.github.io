## No development of abbreviations

All abbreviations will be retained in the transcriptions, as their development is subject to interpretation and differs according to the usage and language of the scribe.

In the current state of automated transcription tools, which operate only at the line level, without context, and without taking into account the language of the source document, the development of abbreviations in transcription data is likely to lead to aberrations and reduce the quality of predictions. We consider that the development of abbreviations should be carried out as an independent normalization task following the transcription step. 

For **medieval documents**, [MUFI](https://mufi.info/q.php?p=mufi/home) must be preferred along with Unicode's public domain characters. We draw the attention to the wide variety of characters proposed by MUFI, some of which are very similar or even indistinguishable without in-depth visual comparison. This is the case for the Armenian letter ք (Ke) [U+0554], which has strong similarities with ꝑ [U+A751], the latter being the correct letter to represent the p with stroke through descender. 

The characters used most frequently by CATMuS are all listed in the character table section of the CATMuS website. 

The abbreviations were organized into the following categories: 

- Tildes
- Abbreviations using superscript letters.
- Abbreviations using special signs: strikethrough letters (d, l, p, q) are among the most common. 

Should other special signs be required (such as ħ or ẜ), each project is free to add the signs it needs, provided it is documented and based on the characters proposed by MUFI.

In **modern and contemporary documents**, abbreviations more often take the form of superscripted letters as in "1ˢᵗ" for *first*, of "Mᵉˡˡᵉ" for *Mademoiselle*, although for older documents, the abbreviation system is necessarily closer to medieval practices with the use of characters such as tildas ("~" [U+007E]) <!-- AC: todo: double check the unicode identifier--> and "ꝑ", as shown above. Thus, certain common abbreviation signs are used as in medieval documents, like "ꝑ" [U+A751], "⁊" [U+204A] and "ɖ" [U+0256]. <!-- AC: todo: update this once I work on the characters part -->

For superscripted text, three phenomenons should be distinguished:

1. when a unique letter is used above a word, as can be found in medieval documents, we use a combining letter corresponding to a superscripted letter, added to the character it relates to, as is the case in the guidelines for medieval documents. <!-- AC: todo: add an example -->

2. when a string of text floats above the text line and is not part of an abbreviation, it is in fact a interlinear correction and should be handled as a separate text line.

3. for sequential additions, as shown above in "1ˢᵗ", we use a markup character, "^" [U+005E] to mark the start of the superscripted sequence, then proceed to use normal characters to transcribe the sequence. The space or a punctuation sign would mark the end of the sequence. Thus "1ˢᵗ" should be transcribe as "1^st". It is important to note that abbreviation markers on the source, like ".", "-" or "=", sometimes traced under the superscripted text, should not be transcribed. We would thus reject "1.^st" or "1^st." (unless "." marks the end of the sentence on the source). 

In the case of commonly found superscripted characters, like "°" (as in "n°", "numero"), they should follow the same rule as presented above and be transcribed as "n^o".
