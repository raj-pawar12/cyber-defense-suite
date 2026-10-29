# Viva cheat sheet

**What problem does it solve?** Phishing links and messages imitate trusted brands. People cannot spot them reliably, and blocklists miss new ones. The suite estimates the risk from text alone and explains the reasons.

**Why analyse only the text?** It is fast, safe (a malicious page is never opened), works on brand-new links and needs no network access. The trade-off is that it cannot see the page content.

**What features does the URL model use?** 31 numbers: lengths, dots, hyphens, digits, IP address host, @ sign, HTTPS, subdomain count, risky ending, free hosting, shortener, brand name on the wrong domain (with look-alike detection), entropy, punycode and more.

**Which models were compared and why Random Forest?** Logistic Regression, Decision Tree, Random Forest, Hist Gradient Boosting and a character n-gram model, using 5-fold cross-validation on the training set only. The best F1 is deployed; the test set is touched once.

**Why are the scores so high?** The data is synthetic and generated from patterns, so it is easier than real traffic. The README explains how to retrain on PhishTank/OpenPhish data. Expect lower numbers on real data.

**How do you avoid data leakage?** Stratified split first, cross-validation only inside the training set, duplicates removed.

**How are predictions explained?** Rule-based warning signs, plus occlusion: replace one feature with its typical value and see how much the probability falls.

**How does the message engine work?** Clean the text (mask links, numbers), TF-IDF word and bigram features, then a linear classifier. Every link is also scored by Module 1; the final score is the maximum of the two.

**What is RAG and how is it used?** Retrieval-augmented generation: find the most relevant passages in a trusted knowledge base and give them to the language model so its answer is grounded and citable. Retrieval here is TF-IDF cosine similarity.

**How is Gemini integrated?** A small REST client calls the `generateContent` endpoint with the key in a header. The prompt contains a system instruction, history, retrieved passages and tool results. Errors fall back to offline mode.

**How do you keep the chatbot safe?** Keyword guardrails before the model, a system prompt with safety rules and instructions to treat supplied text as data, no storage of chat text, rate limiting, and a warning not to type secrets.

**What are the limitations?** Text-only detection, synthetic training data, shorteners are flagged, Gemini can be wrong, small knowledge base, in-memory rate limiter.

**Future work?** Real datasets, WHOIS/TLS features, neural models, embedding retrieval, browser extension, retraining from feedback.
