<span class="rule">Abbreviations MUST NOT be developped</span>.

In the current state of automated transcription tools, which operate only at the line level, without context, and without taking into account the language of the source document, the development of abbreviations in transcription data is likely to lead to aberrations and reduce the quality of predictions. We consider that the development of abbreviations should be carried out as an independent normalization task following the transcription step.

## In medieval documents

[MUFI](https://mufi.info/q.php?p=mufi/home) MUST be preferred along with Unicode's public domain characters. We draw the attention to the wide variety of characters proposed by MUFI, some of which are very similar or even indistinguishable without in-depth visual comparison. This is the case for the Armenian letter ք (Ke) [U+0554], which has strong similarities with ꝑ [U+A751], the latter being the correct letter to represent the p with stroke through descender.

<!-- AC: this should be rephrased into sets of rules rather than a guide on how to use the character table. -->

The characters used most frequently by CATMuS are all listed in the character table section of the CATMuS website. 

The abbreviations were organized into the following categories: 

- Tildes <!-- "~" [U+007E] -->
- Abbreviations using superscript letters.
- Abbreviations using special signs: strikethrough letters (d, l, p, q) are among the most common. 

Should other special signs be required (such as ħ or ẜ), each project MAY add the signs it needs, provided it is documented and based on the characters proposed by MUFI.

## In modern and contemporary documents

For older documents, when the abbreviation system is closer to medieval practices, the rules listed above MAY apply.

For commonly abbreviated letters, such as "ꝑ" [U+A751], "⁊" [U+204A] and "ɖ" [U+0256], they MAY be retained for the transcription of more recent sources.

Most frequently in modern and contemporary documents, abbreviations take the form of superscripted letters (as in "1ˢᵗ" for *first*, of "Mᵉˡˡᵉ" for *Mademoiselle*). They must be transcribed following the distinction of three phenomenons:

1. <span class="rule">Superscript sequential additions MUST be transcribed using a pseudo markup system based on "^" [U+005E], which marks the beginning of the sequence.</span> Therefore, "1ˢᵗ" MUST be transcribed as "1^st".

    - <span class="rule">Abbreviation markers associated to superscript text MUST not be transcribed.</span> Therefore, "1ˢᵗ" MUST not be transcribed as "1.st", "1.^st", "1=st" or "1^st." (unless, in the latter, "." marks the end of a sentence in the source).

    - Commonly found equivalent to superscript characters, such as "°" MUST not be used as a replacement to this rule. Therefore "n°" MUST be transcribed as "n^o" and not "n°".

2. <span class="rule">Interlinear corrections MUST NOT be confused with superscript sequential additions</span>.

3. <span class="rule">In modern documents, a unique letter used above a word, as can be found in medieval documents, MAY be transcribed with the corresponding combining letter, combined to the character it relates to</span>.
