- Properties cite §9, even if §5 repeats the value.
- Compatibility answers name the class: “Bleach is a strong oxidizer; §10 lists strong oxidizing agents as incompatible.”
- “No information available” counts as answerable. The gold answer is “The SDS provides no data for X”, with the citation.
- The citation is the (doc, section, page) where the key fact appears. If the answer needs two places (for example §2 and §10 for sodium azide plus acid), put the main one in gold_citation and add "also_cited" for the other.
- Gold answers are short: only the facts a correct answer must contain, with units exactly as on the sheet.
- OSHA PEL means the current (non-vacated) value. If only vacated values exist, the gold answer says so.
- Unanswerable examples get gold_answer: "REFUSE" and gold_citation: null.

###Example row
{"id": 12, "question": "Can I store sodium azide next to hydrochloric acid?",
 "gold_answer": "No. Acids are incompatible; contact with acids releases very toxic gas.",
 "gold_citation": {"doc": "sodium_azide_fisher.pdf", "section": 10, "page": 5},
 "also_cited": [{"doc": "sodium_azide_fisher.pdf", "section": 2, "page": 2}],
 "category": "compatibility", "answerable": true, "labeler": "bakhtiar"}