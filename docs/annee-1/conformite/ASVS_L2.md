# OWASP ASVS 4.0.3 — niveau 2 : statut de chaque exigence

> **Construit — branche `annee-1`, pas dans la démo.** Auto-évaluation de l'équipe, PAS un audit externe ni une
> certification. Généré par `python prototype/scripts/asvs_l2.py` depuis le fichier officiel de l'OWASP
> (`asvs-4.0.3-en.csv`, CC BY-SA 3.0). Une exigence n'est « conforme » qu'avec une preuve (test ou fichier) ;
> sans examen, elle reste « non évaluée ».

**259 exigences de niveau 2** : conforme : 30 · partiel : 21 · non conforme : 2 · sans objet : 23 · non évaluée : 183

| Exigence | Intitulé (OWASP, anglais) | Statut | Preuve |
|---|---|---|---|
| V1.1.1 | Verify the use of a secure software development lifecycle that addresses security in all stages of development. | non évaluée |  |
| V1.1.2 | Verify the use of threat modeling for every design change or sprint planning to identify threats, plan for countermeasures, facilitate appropriate risk response… | non évaluée |  |
| V1.1.3 | Verify that all user stories and features contain functional security constraints, such as "As a user, I should be able to view and edit my profile. I should no… | non évaluée |  |
| V1.1.4 | Verify documentation and justification of all the application's trust boundaries, components, and significant data flows. | non évaluée |  |
| V1.1.5 | Verify definition and security analysis of the application's high-level architecture and all connected remote services. | non évaluée |  |
| V1.1.6 | Verify implementation of centralized, simple (economy of design), vetted, secure, and reusable security controls to avoid duplicate, missing, ineffective, or in… | non évaluée |  |
| V1.1.7 | Verify availability of a secure coding checklist, security requirements, guideline, or policy to all developers and testers. | non évaluée |  |
| V1.2.1 | Verify the use of unique or special low-privilege operating system accounts for all application components, services, and servers. | non évaluée |  |
| V1.2.2 | Verify that communications between application components, including APIs, middleware and data layers, are authenticated. Components should have the least neces… | non évaluée |  |
| V1.2.3 | Verify that the application uses a single vetted authentication mechanism that is known to be secure, can be extended to include strong authentication, and has … | non évaluée |  |
| V1.2.4 | Verify that all authentication pathways and identity management APIs implement consistent authentication security control strength, such that there are no weake… | non évaluée |  |
| V1.4.1 | Verify that trusted enforcement points, such as access control gateways, servers, and serverless functions, enforce access controls. Never enforce access contro… | non évaluée |  |
| V1.4.4 | Verify the application uses a single and well-vetted access control mechanism for accessing protected data and resources. All requests must pass through this si… | non évaluée |  |
| V1.4.5 | Verify that attribute or feature-based access control is used whereby the code checks the user's authorization for a feature/data item rather than just their ro… | non évaluée |  |
| V1.5.1 | Verify that input and output requirements clearly define how to handle and process data based on type, content, and applicable laws, regulations, and other poli… | non évaluée |  |
| V1.5.2 | Verify that serialization is not used when communicating with untrusted clients. If this is not possible, ensure that adequate integrity controls (and possibly … | non évaluée |  |
| V1.5.3 | Verify that input validation is enforced on a trusted service layer. | non évaluée |  |
| V1.5.4 | Verify that output encoding occurs close to or by the interpreter for which it is intended. | non évaluée |  |
| V1.6.1 | Verify that there is an explicit policy for management of cryptographic keys and that a cryptographic key lifecycle follows a key management standard such as NI… | non évaluée |  |
| V1.6.2 | Verify that consumers of cryptographic services protect key material and other secrets by using key vaults or API based alternatives. | non évaluée |  |
| V1.6.3 | Verify that all keys and passwords are replaceable and are part of a well-defined process to re-encrypt sensitive data. | non évaluée |  |
| V1.6.4 | Verify that the architecture treats client-side secrets--such as symmetric keys, passwords, or API tokens--as insecure and never uses them to protect or access … | non évaluée |  |
| V1.7.1 | Verify that a common logging format and approach is used across the system. | non évaluée |  |
| V1.7.2 | Verify that logs are securely transmitted to a preferably remote system for analysis, detection, alerting, and escalation. | non évaluée |  |
| V1.8.1 | Verify that all sensitive data is identified and classified into protection levels. | non évaluée |  |
| V1.8.2 | Verify that all protection levels have an associated set of protection requirements, such as encryption requirements, integrity requirements, retention, privacy… | non évaluée |  |
| V1.9.1 | Verify the application encrypts communications between components, particularly when these components are in different containers, systems, sites, or cloud prov… | non évaluée |  |
| V1.9.2 | Verify that application components verify the authenticity of each side in a communication link to prevent person-in-the-middle attacks. For example, applicatio… | non évaluée |  |
| V1.10.1 | Verify that a source code control system is in use, with procedures to ensure that check-ins are accompanied by issues or change tickets. The source code contro… | non évaluée |  |
| V1.11.1 | Verify the definition and documentation of all application components in terms of the business or security functions they provide. | non évaluée |  |
| V1.11.2 | Verify that all high-value business logic flows, including authentication, session management and access control, do not share unsynchronized state. | non évaluée |  |
| V1.12.2 | Verify that user-uploaded files - if required to be displayed or downloaded from the application - are served by either octet stream downloads, or from an unrel… | non évaluée |  |
| V1.14.1 | Verify the segregation of components of differing trust levels through well-defined security controls, firewall rules, API gateways, reverse proxies, cloud-base… | non évaluée |  |
| V1.14.2 | Verify that binary signatures, trusted connections, and verified endpoints are used to deploy binaries to remote devices. | non évaluée |  |
| V1.14.3 | Verify that the build pipeline warns of out-of-date or insecure components and takes appropriate actions. | non évaluée |  |
| V1.14.4 | Verify that the build pipeline contains a build step to automatically build and verify the secure deployment of the application, particularly if the application… | non évaluée |  |
| V1.14.5 | Verify that application deployments adequately sandbox, containerize and/or isolate at the network level to delay and deter attackers from attacking other appli… | non évaluée |  |
| V1.14.6 | Verify the application does not use unsupported, insecure, or deprecated client-side technologies such as NSAPI plugins, Flash, Shockwave, ActiveX, Silverlight,… | non évaluée |  |
| V2.1.1 | Verify that user set passwords are at least 12 characters in length (after multiple spaces are combined). | sans objet | aucun mot de passe : invitation à usage unique + second facteur TOTP (lot 2) |
| V2.1.2 | Verify that passwords of at least 64 characters are permitted, and that passwords of more than 128 characters are denied. | sans objet | aucun mot de passe : invitation à usage unique + second facteur TOTP (lot 2) |
| V2.1.3 | Verify that password truncation is not performed. However, consecutive multiple spaces may be replaced by a single space. | sans objet | aucun mot de passe : invitation à usage unique + second facteur TOTP (lot 2) |
| V2.1.4 | Verify that any printable Unicode character, including language neutral characters such as spaces and Emojis are permitted in passwords. | sans objet | aucun mot de passe : invitation à usage unique + second facteur TOTP (lot 2) |
| V2.1.5 | Verify users can change their password. | sans objet | aucun mot de passe : invitation à usage unique + second facteur TOTP (lot 2) |
| V2.1.6 | Verify that password change functionality requires the user's current and new password. | sans objet | aucun mot de passe : invitation à usage unique + second facteur TOTP (lot 2) |
| V2.1.7 | Verify that passwords submitted during account registration, login, and password change are checked against a set of breached passwords either locally (such as … | sans objet | aucun mot de passe : invitation à usage unique + second facteur TOTP (lot 2) |
| V2.1.8 | Verify that a password strength meter is provided to help users set a stronger password. | sans objet | aucun mot de passe : invitation à usage unique + second facteur TOTP (lot 2) |
| V2.1.9 | Verify that there are no password composition rules limiting the type of characters permitted. There should be no requirement for upper or lower case or numbers… | sans objet | aucun mot de passe : invitation à usage unique + second facteur TOTP (lot 2) |
| V2.1.10 | Verify that there are no periodic credential rotation or password history requirements. | sans objet | aucun mot de passe : invitation à usage unique + second facteur TOTP (lot 2) |
| V2.1.11 | Verify that "paste" functionality, browser password helpers, and external password managers are permitted. | sans objet | aucun mot de passe : invitation à usage unique + second facteur TOTP (lot 2) |
| V2.1.12 | Verify that the user can choose to either temporarily view the entire masked password, or temporarily view the last typed character of the password on platforms… | sans objet | aucun mot de passe : invitation à usage unique + second facteur TOTP (lot 2) |
| V2.2.1 | Verify that anti-automation controls are effective at mitigating breached credential testing, brute force, and account lockout attacks. Such controls include bl… | partiel | limite d'écritures par session (test_limite_par_session) ; pas de blocage après des codes TOTP faux (AUDIT_LOT23 M2) |
| V2.2.2 | Verify that the use of weak authenticators (such as SMS and email) is limited to secondary verification and transaction approval and not as a replacement for mo… | non évaluée |  |
| V2.2.3 | Verify that secure notifications are sent to users after updates to authentication details, such as credential resets, email or address changes, logging in from… | non évaluée |  |
| V2.3.1 | Verify system generated initial passwords or activation codes SHOULD be securely randomly generated, SHOULD be at least 6 characters long, and MAY contain lette… | conforme | invitation : jeton aléatoire signé, usage unique, expiration (test_invitation_a_usage_unique_et_qui_expire) |
| V2.3.2 | Verify that enrollment and use of user-provided authentication devices are supported, such as a U2F or FIDO tokens. | non évaluée |  |
| V2.3.3 | Verify that renewal instructions are sent with sufficient time to renew time bound authenticators. | non évaluée |  |
| V2.4.1 | Verify that passwords are stored in a form that is resistant to offline attacks. Passwords SHALL be salted and hashed using an approved one-way key derivation o… | sans objet | aucun mot de passe : invitation à usage unique + second facteur TOTP (lot 2) |
| V2.4.2 | Verify that the salt is at least 32 bits in length and be chosen arbitrarily to minimize salt value collisions among stored hashes. For each credential, a uniqu… | sans objet | aucun mot de passe : invitation à usage unique + second facteur TOTP (lot 2) |
| V2.4.3 | Verify that if PBKDF2 is used, the iteration count SHOULD be as large as verification server performance will allow, typically at least 100,000 iterations. | sans objet | aucun mot de passe : invitation à usage unique + second facteur TOTP (lot 2) |
| V2.4.4 | Verify that if bcrypt is used, the work factor SHOULD be as large as verification server performance will allow, with a minimum of 10. | sans objet | aucun mot de passe : invitation à usage unique + second facteur TOTP (lot 2) |
| V2.4.5 | Verify that an additional iteration of a key derivation function is performed, using a salt value that is secret and known only to the verifier. Generate the sa… | sans objet | aucun mot de passe : invitation à usage unique + second facteur TOTP (lot 2) |
| V2.5.1 | Verify that a system generated initial activation or recovery secret is not sent in clear text to the user. | conforme | le jeton d'invitation n'est jamais écrit dans le journal (test_aucun_secret_en_clair_dans_le_journal) |
| V2.5.2 | Verify password hints or knowledge-based authentication (so-called "secret questions") are not present. | conforme | aucune question secrète ni indice (comptes.py) |
| V2.5.3 | Verify password credential recovery does not reveal the current password in any way. | sans objet | aucun mot de passe : invitation à usage unique + second facteur TOTP (lot 2) |
| V2.5.4 | Verify shared or default accounts are not present (e.g. "root", "admin", or "sa"). | partiel | comptes nominatifs (lots 2-4) ; MAIS le jeton « console » de la DÉMO est un secret partagé qui peut incarner chaque membre (audit des lots 6-8) |
| V2.5.5 | Verify that if an authentication factor is changed or replaced, that the user is notified of this event. | partiel | remplacement du second facteur journalisé (ADMIN_ACTION « remplacer_totp ») ; pas encore d'avis envoyé au membre |
| V2.5.6 | Verify forgotten password, and other recovery paths use a secure recovery mechanism, such as time-based OTP (TOTP) or other soft token, mobile push, or another … | non évaluée |  |
| V2.5.7 | Verify that if OTP or multi-factor authentication factors are lost, that evidence of identity proofing is performed at the same level as during enrollment. | non évaluée |  |
| V2.6.1 | Verify that lookup secrets can be used only once. | non évaluée |  |
| V2.6.2 | Verify that lookup secrets have sufficient randomness (112 bits of entropy), or if less than 112 bits of entropy, salted with a unique and random 32-bit salt an… | non évaluée |  |
| V2.6.3 | Verify that lookup secrets are resistant to offline attacks, such as predictable values. | non évaluée |  |
| V2.7.1 | Verify that clear text out of band (NIST "restricted") authenticators, such as SMS or PSTN, are not offered by default, and stronger alternatives such as push n… | conforme | aucun SMS ni appel n'authentifie (les SMS du lot 5 sont des notifications) |
| V2.7.2 | Verify that the out of band verifier expires out of band authentication requests, codes, or tokens after 10 minutes. | non évaluée |  |
| V2.7.3 | Verify that the out of band verifier authentication requests, codes, or tokens are only usable once, and only for the original authentication request. | non évaluée |  |
| V2.7.4 | Verify that the out of band authenticator and verifier communicates over a secure independent channel. | non évaluée |  |
| V2.7.5 | Verify that the out of band verifier retains only a hashed version of the authentication code. | non évaluée |  |
| V2.7.6 | Verify that the initial authentication code is generated by a secure random number generator, containing at least 20 bits of entropy (typically a six digital ra… | non évaluée |  |
| V2.8.1 | Verify that time-based OTPs have a defined lifetime before expiring. | conforme | TOTP RFC 6238, pas de 30 s, ±1 pas toléré (test_le_code_totp_tolere_un_pas_de_decalage_pas_plus) |
| V2.8.2 | Verify that symmetric keys used to verify submitted OTPs are highly protected, such as by using a hardware security module or secure operating system based key … | partiel | secret TOTP dérivé du secret du serveur + nonce journalisé, jamais stocké en clair ; pas de module matériel |
| V2.8.3 | Verify that approved cryptographic algorithms are used in the generation, seeding, and verification of OTPs. | conforme | HMAC-SHA1 RFC 6238, vecteur de la RFC vérifié (test_le_vecteur_de_la_rfc_6238_est_respecte) |
| V2.8.4 | Verify that time-based OTP can be used only once within the validity period. | conforme | un code ne sert qu'une fois (test_la_console_exige_un_compte_nominatif_et_le_code_totp) |
| V2.8.5 | Verify that if a time-based multi-factor OTP token is re-used during the validity period, it is logged and rejected with secure notifications being sent to the … | partiel | rejeu refusé ; pas encore consigné comme événement de sécurité |
| V2.8.6 | Verify physical single-factor OTP generator can be revoked in case of theft or other loss. Ensure that revocation is immediately effective across logged in sess… | non évaluée |  |
| V2.8.7 | Verify that biometric authenticators are limited to use only as secondary factors in conjunction with either something you have and something you know. | non évaluée |  |
| V2.9.1 | Verify that cryptographic keys used in verification are stored securely and protected against disclosure, such as using a Trusted Platform Module (TPM) or Hardw… | non évaluée |  |
| V2.9.2 | Verify that the challenge nonce is at least 64 bits in length, and statistically unique or unique over the lifetime of the cryptographic device. | non évaluée |  |
| V2.9.3 | Verify that approved cryptographic algorithms are used in the generation, seeding, and verification. | non évaluée |  |
| V2.10.1 | Verify that intra-service secrets do not rely on unchanging credentials such as passwords, API keys or shared accounts with privileged access. | non évaluée |  |
| V2.10.2 | Verify that if passwords are required for service authentication, the service account used is not a default credential. (e.g. root/root or admin/admin are defau… | non évaluée |  |
| V2.10.3 | Verify that passwords are stored with sufficient protection to prevent offline recovery attacks, including local system access. | non évaluée |  |
| V2.10.4 | Verify passwords, integrations with databases and third-party systems, seeds and internal secrets, and API keys are managed securely and not included in the sou… | conforme | secrets par l'environnement seulement (CONFIGURATION.md, verifier_secrets, test_le_depot_est_propre) |
| V3.1.1 | Verify the application never reveals session tokens in URL parameters. | partiel | comptes : session en en-tête ; MAIS le téléphone de la démo accepte ?session= (régie, app.html) — audit des lots 6-8 |
| V3.2.1 | Verify the application generates a new session token on user authentication. | conforme | nouvelle session à chaque acceptation (comptes.accepter) |
| V3.2.2 | Verify that session tokens possess at least 64 bits of entropy. | conforme | identifiant de session secrets.token_urlsafe(12) = 96 bits, signé HMAC-SHA256 |
| V3.2.3 | Verify the application only stores session tokens in the browser using secure methods such as appropriately secured cookies (see section 3.4) or HTML 5 session … | partiel | sessionStorage (onglet seulement), pas de cookie ; un script injecté pourrait la lire (pas de cookie HttpOnly) |
| V3.2.4 | Verify that session tokens are generated using approved cryptographic algorithms. | conforme | HMAC-SHA256 (comptes._mac) |
| V3.3.1 | Verify that logout and expiration invalidate the session token, such that the back button or a downstream relying party does not resume an authenticated session… | partiel | comptes : déconnexion et expiration (test_sessions_appareils_et_deconnexion) ; sessions de membre de la démo sans état côté serveur |
| V3.3.2 | If authenticators permit users to remain logged in, verify that re-authentication occurs periodically both when actively used or after an idle period. | partiel | console : élévation de 12 h ; MAIS session de compte de 30 jours sans délai d'inactivité (le niveau 2 demande 12 h ou 30 min d'inactivité) |
| V3.3.3 | Verify that the application gives the option to terminate all other active sessions after a successful password change (including change via password reset/reco… | non évaluée |  |
| V3.3.4 | Verify that users are able to view and (having re-entered login credentials) log out of any or all currently active sessions and devices. | partiel | comptes : liste et déconnexion des appareils ; pas pour les sessions de membre de la démo |
| V3.4.1 | Verify that cookie-based session tokens have the 'Secure' attribute set. | sans objet | aucun cookie de session (en-tête) |
| V3.4.2 | Verify that cookie-based session tokens have the 'HttpOnly' attribute set. | sans objet | aucun cookie de session (en-tête) |
| V3.4.3 | Verify that cookie-based session tokens utilize the 'SameSite' attribute to limit exposure to cross-site request forgery attacks. | sans objet | aucun cookie de session (en-tête) |
| V3.4.4 | Verify that cookie-based session tokens use the "__Host-" prefix so cookies are only sent to the host that initially set the cookie. | sans objet | aucun cookie de session (en-tête) |
| V3.4.5 | Verify that if the application is published under a domain name with other applications that set or use session cookies that might disclose the session cookies,… | sans objet | aucun cookie de session (en-tête) |
| V3.5.1 | Verify the application allows users to revoke OAuth tokens that form trust relationships with linked applications. | non évaluée |  |
| V3.5.2 | Verify the application uses session tokens rather than static API secrets and keys, except with legacy implementations. | partiel | sessions par personne pour les comptes ; le jeton « console » de la DÉMO reste un secret partagé |
| V3.5.3 | Verify that stateless session tokens use digital signatures, encryption, and other countermeasures to protect against tampering, enveloping, replay, null cipher… | conforme | jeton de session signé HMAC, expiration couverte par la signature |
| V3.7.1 | Verify the application ensures a full, valid login session or requires re-authentication or secondary verification before allowing any sensitive transactions or… | conforme | actions d'administration : session élevée par un code exigée (AUDIT_LOT23 I1) |
| V4.1.1 | Verify that the application enforces access control rules on a trusted service layer, especially if client-side access control is present and could be bypassed. | conforme | contrôles côté serveur ; balayage automatique de chaque route (test_autorisation_balayage.py) |
| V4.1.2 | Verify that all user and data attributes and policy information used by access controls cannot be manipulated by end users unless specifically authorized. | non évaluée |  |
| V4.1.3 | Verify that the principle of least privilege exists - users should only be able to access functions, data files, URLs, controllers, services, and other resource… | conforme | rôles membre / invité / secrétariat / administration ; le secrétariat ne voit que membres et invités |
| V4.1.5 | Verify that access controls fail securely including when an exception occurs. | conforme | toute erreur métier → 401/403/404/409 ; balayage : aucune route ne s'ouvre sur une session fausse |
| V4.2.1 | Verify that sensitive data and APIs are protected against Insecure Direct Object Reference (IDOR) attacks targeting creation, reading, updating and deletion of … | conforme | « moi » = la session, jamais un identifiant passé par le client (test_on_ne_deconnecte_pas_l_appareil_d_un_autre) |
| V4.2.2 | Verify that the application or framework enforces a strong anti-CSRF mechanism to protect authenticated functionality, and effective anti-automation or anti-CSR… | conforme | session en en-tête personnalisé + refus des Origin étrangères (test_une_origine_etrangere_est_refusee) |
| V4.3.1 | Verify administrative interfaces use appropriate multi-factor authentication to prevent unauthorized use. | conforme | console du secrétariat : compte nominatif + TOTP + élévation (test_seul_un_compte_nominatif_eleve_ouvre_la_console) |
| V4.3.2 | Verify that directory browsing is disabled unless deliberately desired. Additionally, applications should not allow discovery or disclosure of file or directory… | conforme | aucune liste de répertoire (FastAPI, fichiers statiques nommés) |
| V4.3.3 | Verify the application has additional authorization (such as step up or adaptive authentication) for lower value systems, and / or segregation of duties for hig… | non évaluée |  |
| V5.1.1 | Verify that the application has defenses against HTTP parameter pollution attacks, particularly if the application framework makes no distinction about the sour… | non évaluée |  |
| V5.1.2 | Verify that frameworks protect against mass parameter assignment attacks, or that the application has countermeasures to protect against unsafe parameter assign… | non évaluée |  |
| V5.1.3 | Verify that all input (HTML form fields, REST requests, URL parameters, HTTP headers, cookies, batch files, RSS feeds, etc) is validated using positive validati… | non évaluée |  |
| V5.1.4 | Verify that structured data is strongly typed and validated against a defined schema including allowed characters, length and pattern (e.g. credit card numbers,… | non évaluée |  |
| V5.1.5 | Verify that URL redirects and forwards only allow destinations which appear on an allow list, or show a warning when redirecting to potentially untrusted conten… | non évaluée |  |
| V5.2.1 | Verify that all untrusted HTML input from WYSIWYG editors or similar is properly sanitized with an HTML sanitizer library or framework feature. | non évaluée |  |
| V5.2.2 | Verify that unstructured data is sanitized to enforce safety measures such as allowed characters and length. | non évaluée |  |
| V5.2.3 | Verify that the application sanitizes user input before passing to mail systems to protect against SMTP or IMAP injection. | non évaluée |  |
| V5.2.4 | Verify that the application avoids the use of eval() or other dynamic code execution features. Where there is no alternative, any user input being included must… | non évaluée |  |
| V5.2.5 | Verify that the application protects against template injection attacks by ensuring that any user input being included is sanitized or sandboxed. | non évaluée |  |
| V5.2.6 | Verify that the application protects against SSRF attacks, by validating or sanitizing untrusted data or HTTP file metadata, such as filenames and URL input fie… | non évaluée |  |
| V5.2.7 | Verify that the application sanitizes, disables, or sandboxes user-supplied Scalable Vector Graphics (SVG) scriptable content, especially as they relate to XSS … | non évaluée |  |
| V5.2.8 | Verify that the application sanitizes, disables, or sandboxes user-supplied scriptable or expression template language content, such as Markdown, CSS or XSL sty… | non évaluée |  |
| V5.3.1 | Verify that output encoding is relevant for the interpreter and context required. For example, use encoders specifically for HTML values, HTML attributes, JavaS… | non évaluée |  |
| V5.3.2 | Verify that output encoding preserves the user's chosen character set and locale, such that any Unicode character point is valid and safely handled. | non évaluée |  |
| V5.3.3 | Verify that context-aware, preferably automated - or at worst, manual - output escaping protects against reflected, stored, and DOM based XSS. | non évaluée |  |
| V5.3.4 | Verify that data selection or database queries (e.g. SQL, HQL, ORM, NoSQL) use parameterized queries, ORMs, entity frameworks, or are otherwise protected from d… | non évaluée |  |
| V5.3.5 | Verify that where parameterized or safer mechanisms are not present, context-specific output encoding is used to protect against injection attacks, such as the … | non évaluée |  |
| V5.3.6 | Verify that the application protects against JSON injection attacks, JSON eval attacks, and JavaScript expression evaluation. | non évaluée |  |
| V5.3.7 | Verify that the application protects against LDAP injection vulnerabilities, or that specific security controls to prevent LDAP injection have been implemented. | non évaluée |  |
| V5.3.8 | Verify that the application protects against OS command injection and that operating system calls use parameterized OS queries or use contextual command line ou… | non évaluée |  |
| V5.3.9 | Verify that the application protects against Local File Inclusion (LFI) or Remote File Inclusion (RFI) attacks. | non évaluée |  |
| V5.3.10 | Verify that the application protects against XPath injection or XML injection attacks. | non évaluée |  |
| V5.4.1 | Verify that the application uses memory-safe string, safer memory copy and pointer arithmetic to detect or prevent stack, buffer, or heap overflows. | non évaluée |  |
| V5.4.2 | Verify that format strings do not take potentially hostile input, and are constant. | non évaluée |  |
| V5.4.3 | Verify that sign, range, and input validation techniques are used to prevent integer overflows. | non évaluée |  |
| V5.5.1 | Verify that serialized objects use integrity checks or are encrypted to prevent hostile object creation or data tampering. | non évaluée |  |
| V5.5.2 | Verify that the application correctly restricts XML parsers to only use the most restrictive configuration possible and to ensure that unsafe features such as r… | non évaluée |  |
| V5.5.3 | Verify that deserialization of untrusted data is avoided or is protected in both custom code and third-party libraries (such as JSON, XML and YAML parsers). | non évaluée |  |
| V5.5.4 | Verify that when parsing JSON in browsers or JavaScript-based backends, JSON.parse is used to parse the JSON document. Do not use eval() to parse JSON. | non évaluée |  |
| V6.1.1 | Verify that regulated private data is stored encrypted while at rest, such as Personally Identifiable Information (PII), sensitive personal information, or data… | non évaluée |  |
| V6.1.2 | Verify that regulated health data is stored encrypted while at rest, such as medical records, medical device details, or de-anonymized research records. | non évaluée |  |
| V6.1.3 | Verify that regulated financial data is stored encrypted while at rest, such as financial accounts, defaults or credit history, tax records, pay history, benefi… | non évaluée |  |
| V6.2.1 | Verify that all cryptographic modules fail securely, and errors are handled in a way that does not enable Padding Oracle attacks. | non évaluée |  |
| V6.2.2 | Verify that industry proven or government approved cryptographic algorithms, modes, and libraries are used, instead of custom coded cryptography. | non évaluée |  |
| V6.2.3 | Verify that encryption initialization vector, cipher configuration, and block modes are configured securely using the latest advice. | non évaluée |  |
| V6.2.4 | Verify that random number, encryption or hashing algorithms, key lengths, rounds, ciphers or modes, can be reconfigured, upgraded, or swapped at any time, to pr… | non évaluée |  |
| V6.2.5 | Verify that known insecure block modes (i.e. ECB, etc.), padding modes (i.e. PKCS#1 v1.5, etc.), ciphers with small block sizes (i.e. Triple-DES, Blowfish, etc.… | non évaluée |  |
| V6.2.6 | Verify that nonces, initialization vectors, and other single use numbers must not be used more than once with a given encryption key. The method of generation m… | non évaluée |  |
| V6.3.1 | Verify that all random numbers, random file names, random GUIDs, and random strings are generated using the cryptographic module's approved cryptographically se… | non évaluée |  |
| V6.3.2 | Verify that random GUIDs are created using the GUID v4 algorithm, and a Cryptographically-secure Pseudo-random Number Generator (CSPRNG). GUIDs created using ot… | non évaluée |  |
| V6.4.1 | Verify that a secrets management solution such as a key vault is used to securely create, store, control access to and destroy secrets. | non évaluée |  |
| V6.4.2 | Verify that key material is not exposed to the application but instead uses an isolated security module like a vault for cryptographic operations. | non évaluée |  |
| V7.1.1 | Verify that the application does not log credentials or payment details. Session tokens should only be stored in logs in an irreversible, hashed form. | non évaluée |  |
| V7.1.2 | Verify that the application does not log other sensitive data as defined under local privacy laws or relevant security policy. | non évaluée |  |
| V7.1.3 | Verify that the application logs security relevant events including successful and failed authentication events, access control failures, deserialization failur… | non évaluée |  |
| V7.1.4 | Verify that each log event includes necessary information that would allow for a detailed investigation of the timeline when an event happens. | non évaluée |  |
| V7.2.1 | Verify that all authentication decisions are logged, without storing sensitive session tokens or passwords. This should include requests with relevant metadata … | non évaluée |  |
| V7.2.2 | Verify that all access control decisions can be logged and all failed decisions are logged. This should include requests with relevant metadata needed for secur… | non évaluée |  |
| V7.3.1 | Verify that all logging components appropriately encode data to prevent log injection. | non évaluée |  |
| V7.3.3 | Verify that security logs are protected from unauthorized access and modification. | non évaluée |  |
| V7.3.4 | Verify that time sources are synchronized to the correct time and time zone. Strongly consider logging only in UTC if systems are global to assist with post-inc… | non évaluée |  |
| V7.4.1 | Verify that a generic message is shown when an unexpected or security sensitive error occurs, potentially with a unique ID which support personnel can use to in… | non évaluée |  |
| V7.4.2 | Verify that exception handling (or a functional equivalent) is used across the codebase to account for expected and unexpected error conditions. | non évaluée |  |
| V7.4.3 | Verify that a "last resort" error handler is defined which will catch all unhandled exceptions. | non évaluée |  |
| V8.1.1 | Verify the application protects sensitive data from being cached in server components such as load balancers and application caches. | conforme | Cache-Control: no-store sur /api/pulse/ (protections.py) |
| V8.1.2 | Verify that all cached or temporary copies of sensitive data stored on the server are protected from unauthorized access or purged/invalidated after the authori… | non évaluée |  |
| V8.1.3 | Verify the application minimizes the number of parameters in a request, such as hidden fields, Ajax variables, cookies and header values. | non évaluée |  |
| V8.1.4 | Verify the application can detect and alert on abnormal numbers of requests, such as by IP, user, total per hour or day, or whatever makes sense for the applica… | non évaluée |  |
| V8.2.1 | Verify the application sets sufficient anti-caching headers so that sensitive data is not cached in modern browsers. | conforme | Cache-Control: no-store sur les données personnelles et les pages des lots |
| V8.2.2 | Verify that data stored in browser storage (such as localStorage, sessionStorage, IndexedDB, or cookies) does not contain sensitive data. | partiel | la session est en sessionStorage ; avec HACKVS_HORS_LIGNE=1 (lot 11), une réponse donnée hors ligne reste dans localStorage jusqu'à son envoi (ADR 0009, dit dans la politique) |
| V8.2.3 | Verify that authenticated data is cleared from client storage, such as the browser DOM, after the client or session is terminated. | non évaluée |  |
| V8.3.1 | Verify that sensitive data is sent to the server in the HTTP message body or headers, and that query string parameters from any HTTP verb do not contain sensiti… | partiel | invitation et désinscription dans le fragment (#) ; MAIS ?jure=, ?code=, ?session= dans des adresses de la démo |
| V8.3.2 | Verify that users have a method to remove or export their data on demand. | conforme | export et suppression définitive (lot 3, test_annee1_espace_membre*.py, test_annee1_audit_lot23.py) |
| V8.3.3 | Verify that users are provided clear language regarding collection and use of supplied personal information and that users have provided opt-in consent for the … | partiel | politique de confidentialité FR/DE rédigée — à valider par un juriste (conformite/) |
| V8.3.4 | Verify that all sensitive data created and processed by the application has been identified, and ensure that a policy is in place on how to deal with sensitive … | partiel | registre des traitements (conformite/REGISTRE_TRAITEMENTS.md) — à valider par un juriste |
| V8.3.5 | Verify accessing sensitive data is audited (without logging the sensitive data itself), if the data is collected under relevant data protection directives or wh… | partiel | console du secrétariat et administration journalisées, refus compris ; la console de DÉMO (jeton partagé) ne l'est pas |
| V8.3.6 | Verify that sensitive information contained in memory is overwritten as soon as it is no longer required to mitigate memory dumping attacks, using zeroes or ran… | non évaluée |  |
| V8.3.7 | Verify that sensitive or private information that is required to be encrypted, is encrypted using approved algorithms that provide both confidentiality and inte… | non évaluée |  |
| V8.3.8 | Verify that sensitive personal information is subject to data retention classification, such that old or out of date data is deleted automatically, on a schedul… | non conforme | durées de conservation proposées dans le registre, pas encore appliquées automatiquement |
| V9.1.1 | Verify that TLS is used for all client connectivity, and does not fall back to insecure or unencrypted communications. | non évaluée |  |
| V9.1.2 | Verify using up to date TLS testing tools that only strong cipher suites are enabled, with the strongest cipher suites set as preferred. | non évaluée |  |
| V9.1.3 | Verify that only the latest recommended versions of the TLS protocol are enabled, such as TLS 1.2 and TLS 1.3. The latest version of the TLS protocol should be … | non évaluée |  |
| V9.2.1 | Verify that connections to and from the server use trusted TLS certificates. Where internally generated or self-signed certificates are used, the server must be… | non évaluée |  |
| V9.2.2 | Verify that encrypted communications such as TLS is used for all inbound and outbound connections, including for management ports, monitoring, authentication, A… | non évaluée |  |
| V9.2.3 | Verify that all encrypted connections to external systems that involve sensitive information or functions are authenticated. | non évaluée |  |
| V9.2.4 | Verify that proper certification revocation, such as Online Certificate Status Protocol (OCSP) Stapling, is enabled and configured. | non évaluée |  |
| V10.2.1 | Verify that the application source code and third party libraries do not contain unauthorized phone home or data collection capabilities. Where such functionali… | non évaluée |  |
| V10.2.2 | Verify that the application does not ask for unnecessary or excessive permissions to privacy related features or sensors, such as contacts, cameras, microphones… | non évaluée |  |
| V10.3.1 | Verify that if the application has a client or server auto-update feature, updates should be obtained over secure channels and digitally signed. The update code… | non évaluée |  |
| V10.3.2 | Verify that the application employs integrity protections, such as code signing or subresource integrity. The application must not load or execute code from unt… | non évaluée |  |
| V10.3.3 | Verify that the application has protection from subdomain takeovers if the application relies upon DNS entries or DNS subdomains, such as expired domain names, … | non évaluée |  |
| V11.1.1 | Verify that the application will only process business logic flows for the same user in sequential step order and without skipping steps. | non évaluée |  |
| V11.1.2 | Verify that the application will only process business logic flows with all steps being processed in realistic human time, i.e. transactions are not submitted t… | non évaluée |  |
| V11.1.3 | Verify the application has appropriate limits for specific business actions or transactions which are correctly enforced on a per user basis. | non évaluée |  |
| V11.1.4 | Verify that the application has anti-automation controls to protect against excessive calls such as mass data exfiltration, business logic requests, file upload… | non évaluée |  |
| V11.1.5 | Verify the application has business logic limits or validation to protect against likely business risks or threats, identified using threat modeling or similar … | non évaluée |  |
| V11.1.6 | Verify that the application does not suffer from "Time Of Check to Time Of Use" (TOCTOU) issues or other race conditions for sensitive operations. | non évaluée |  |
| V11.1.7 | Verify that the application monitors for unusual events or activity from a business logic perspective. For example, attempts to perform actions out of order or … | non évaluée |  |
| V11.1.8 | Verify that the application has configurable alerting when automated attacks or unusual activity is detected. | non évaluée |  |
| V12.1.1 | Verify that the application will not accept large files that could fill up storage or cause a denial of service. | non évaluée |  |
| V12.1.2 | Verify that the application checks compressed files (e.g. zip, gz, docx, odt) against maximum allowed uncompressed size and against maximum number of files befo… | non évaluée |  |
| V12.1.3 | Verify that a file size quota and maximum number of files per user is enforced to ensure that a single user cannot fill up the storage with too many files, or e… | non évaluée |  |
| V12.2.1 | Verify that files obtained from untrusted sources are validated to be of expected type based on the file's content. | non évaluée |  |
| V12.3.1 | Verify that user-submitted filename metadata is not used directly by system or framework filesystems and that a URL API is used to protect against path traversa… | non évaluée |  |
| V12.3.2 | Verify that user-submitted filename metadata is validated or ignored to prevent the disclosure, creation, updating or removal of local files (LFI). | non évaluée |  |
| V12.3.3 | Verify that user-submitted filename metadata is validated or ignored to prevent the disclosure or execution of remote files via Remote File Inclusion (RFI) or S… | non évaluée |  |
| V12.3.4 | Verify that the application protects against Reflective File Download (RFD) by validating or ignoring user-submitted filenames in a JSON, JSONP, or URL paramete… | non évaluée |  |
| V12.3.5 | Verify that untrusted file metadata is not used directly with system API or libraries, to protect against OS command injection. | non évaluée |  |
| V12.3.6 | Verify that the application does not include and execute functionality from untrusted sources, such as unverified content distribution networks, JavaScript libr… | non évaluée |  |
| V12.4.1 | Verify that files obtained from untrusted sources are stored outside the web root, with limited permissions. | non évaluée |  |
| V12.4.2 | Verify that files obtained from untrusted sources are scanned by antivirus scanners to prevent upload and serving of known malicious content. | non évaluée |  |
| V12.5.1 | Verify that the web tier is configured to serve only files with specific file extensions to prevent unintentional information and source code leakage. For examp… | non évaluée |  |
| V12.5.2 | Verify that direct requests to uploaded files will never be executed as HTML/JavaScript content. | non évaluée |  |
| V12.6.1 | Verify that the web or application server is configured with an allow list of resources or systems to which the server can send requests or load data/files from… | non évaluée |  |
| V13.1.1 | Verify that all application components use the same encodings and parsers to avoid parsing attacks that exploit different URI or file parsing behavior that coul… | non évaluée |  |
| V13.1.3 | Verify API URLs do not expose sensitive information, such as the API key, session tokens etc. | non évaluée |  |
| V13.1.4 | Verify that authorization decisions are made at both the URI, enforced by programmatic or declarative security at the controller or router, and at the resource … | non évaluée |  |
| V13.1.5 | Verify that requests containing unexpected or missing content types are rejected with appropriate headers (HTTP response status 406 Unacceptable or 415 Unsuppor… | non évaluée |  |
| V13.2.1 | Verify that enabled RESTful HTTP methods are a valid choice for the user or action, such as preventing normal users using DELETE or PUT on protected API or reso… | non évaluée |  |
| V13.2.2 | Verify that JSON schema validation is in place and verified before accepting input. | non évaluée |  |
| V13.2.3 | Verify that RESTful web services that utilize cookies are protected from Cross-Site Request Forgery via the use of at least one or more of the following: double… | non évaluée |  |
| V13.2.5 | Verify that REST services explicitly check the incoming Content-Type to be the expected one, such as application/xml or application/json. | non évaluée |  |
| V13.2.6 | Verify that the message headers and payload are trustworthy and not modified in transit. Requiring strong encryption for transport (TLS only) may be sufficient … | non évaluée |  |
| V13.3.1 | Verify that XSD schema validation takes place to ensure a properly formed XML document, followed by validation of each input field before any processing of that… | non évaluée |  |
| V13.3.2 | Verify that the message payload is signed using WS-Security to ensure reliable transport between client and service. | non évaluée |  |
| V13.4.1 | Verify that a query allow list or a combination of depth limiting and amount limiting is used to prevent GraphQL or data layer expression Denial of Service (DoS… | non évaluée |  |
| V13.4.2 | Verify that GraphQL or other data layer authorization logic should be implemented at the business logic layer instead of the GraphQL layer. | non évaluée |  |
| V14.1.1 | Verify that the application build and deployment processes are performed in a secure and repeatable way, such as CI / CD automation, automated configuration man… | partiel | Dockerfile et docker-compose.annee1.yml reproductibles ; image non construite dans cette session |
| V14.1.2 | Verify that compiler flags are configured to enable all available buffer overflow protections and warnings, including stack randomization, data execution preven… | non évaluée |  |
| V14.1.3 | Verify that server configuration is hardened as per the recommendations of the application server and frameworks in use. | non évaluée |  |
| V14.1.4 | Verify that the application, configuration, and all dependencies can be re-deployed using automated deployment scripts, built from a documented and tested runbo… | non évaluée |  |
| V14.2.1 | Verify that all components are up to date, preferably using a dependency checker during build or compile time. | partiel | versions exactes figées (constraints.txt) ; pas de vérificateur de dépendances automatique (CI bloquée) |
| V14.2.2 | Verify that all unneeded features, documentation, sample applications and configurations are removed. | non évaluée |  |
| V14.2.3 | Verify that if application assets, such as JavaScript libraries, CSS or web fonts, are hosted externally on a Content Delivery Network (CDN) or external provide… | non évaluée |  |
| V14.2.4 | Verify that third party components come from pre-defined, trusted and continually maintained repositories. | non évaluée |  |
| V14.2.5 | Verify that a Software Bill of Materials (SBOM) is maintained of all third party libraries in use. | non conforme | pas encore de SBOM (constraints.txt donne les versions exactes, ce n'est pas une SBOM) |
| V14.2.6 | Verify that the attack surface is reduced by sandboxing or encapsulating third party libraries to expose only the required behaviour into the application. | non évaluée |  |
| V14.3.2 | Verify that web or application server and application framework debug modes are disabled in production to eliminate debug features, developer consoles, and unin… | conforme | aucun mode debug ; erreurs 500 sans détail (observabilite, gestionnaire 500) |
| V14.3.3 | Verify that the HTTP headers or any part of the HTTP response do not expose detailed version information of system components. | partiel | pas de version de l'application dans les en-têtes ; l'en-tête server d'uvicorn n'est pas retiré |
| V14.4.1 | Verify that every HTTP response contains a Content-Type header. Also specify a safe character set (e.g., UTF-8, ISO-8859-1) if the content types are text/*, /+x… | partiel | Content-Type toujours posé ; les réponses JSON disent « application/json » sans charset explicite (vérifié) |
| V14.4.2 | Verify that all API responses contain a Content-Disposition: attachment; filename="api.json" header (or other appropriate filename for the content type). | non évaluée |  |
| V14.4.3 | Verify that a Content Security Policy (CSP) response header is in place that helps mitigate impact for XSS attacks like HTML, DOM, JSON, and JavaScript injectio… | conforme | CSP stricte par empreintes de scripts sur chaque page (protections.py, test de la CSP) |
| V14.4.4 | Verify that all responses contain a X-Content-Type-Options: nosniff header. | conforme | X-Content-Type-Options: nosniff sur toutes les réponses (protections.BASE) |
| V14.4.5 | Verify that a Strict-Transport-Security header is included on all responses and for all subdomains, such as Strict-Transport-Security: max-age=15724800; include… | partiel | HSTS posé si HACKVS_HSTS=1 (production derrière HTTPS) ; éteint en démo (test_hsts_seulement_quand_on_le_demande) |
| V14.4.6 | Verify that a suitable Referrer-Policy header is included to avoid exposing sensitive information in the URL through the Referer header to untrusted parties. | conforme | Referrer-Policy: no-referrer |
| V14.4.7 | Verify that the content of a web application cannot be embedded in a third-party site by default and that embedding of the exact resources is only allowed where… | conforme | X-Frame-Options SAMEORIGIN + frame-ancestors ; seul le deck LOCAL peut intégrer l'écran de salle |
| V14.5.1 | Verify that the application server only accepts the HTTP methods in use by the application/API, including pre-flight OPTIONS, and logs/alerts on any requests th… | non évaluée |  |
| V14.5.2 | Verify that the supplied Origin header is not used for authentication or access control decisions, as the Origin header can easily be changed by an attacker. | conforme | l'Origin sert seulement à REFUSER (CSRF), jamais à autoriser |
| V14.5.3 | Verify that the Cross-Origin Resource Sharing (CORS) Access-Control-Allow-Origin header uses a strict allow list of trusted domains and subdomains to match agai… | conforme | aucun en-tête CORS : pas d'origine tierce autorisée |
| V14.5.4 | Verify that HTTP headers added by a trusted proxy or SSO devices, such as a bearer token, are authenticated by the application. | non évaluée |  |
