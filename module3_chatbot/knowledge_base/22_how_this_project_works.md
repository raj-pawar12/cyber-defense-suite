# How the Cyber Defense Suite works

## Three modules
Module 1 is the URL engine. It reads only the text of a link and turns it into about 30 measurements such as length, hyphens, IP addresses, the at sign, brand names on the wrong domain and risky domain endings. A Random Forest style classifier turns these into a probability of phishing, and the page lists plain-English warning signs.

Module 2 is the message engine. It cleans the text of an email or SMS, converts it into TF-IDF word features and uses a classifier. It also extracts every link and scores each one with Module 1. The overall score is the higher of the text score and the worst link score. It can also read a QR code from an image.

Module 3 is this chatbot. It searches a local knowledge base of cybersecurity articles, adds the best passages to the question, and asks the Gemini model to answer using them. If you paste a link or ask whether a message is phishing, it calls Modules 1 and 2 first.

## Limits
The detectors judge how a link or message looks. They do not visit the page, so a clean-looking phishing link can slip through. The demo models are trained on synthetic data, so scores on real traffic will be lower. Treat every result as an estimate, not a guarantee.
