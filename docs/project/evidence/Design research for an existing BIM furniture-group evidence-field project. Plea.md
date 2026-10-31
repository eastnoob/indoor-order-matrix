# Design research for an existing BIM furniture-group evidence-field project. Plea

**Question:** Design research for an existing BIM furniture-group evidence-field project. Please synthesize primary literature, with explicit assumptions and counterexamples, for fair multi-evidence fusion when NO known/learnable domain weights exist, either between packages or within each package's channels. Objects are authored furniture groups (smallest unit), fields are overlapping fuzzy/soft group-to-organization relations, not disjoint clusters or probabilities; one group may strongly support several fields, no sum-to-one across fields. Existing package A supplies geometry gaps/contact/positive-area overlap/status/provenance (currently descriptive, no approved group support scalar). Package B supplies whole-group PCA axis modulo 180°, clarity (λ1−λ2)/(λ1+λ2), pairwise angle gap, cos² gap, 1−abs clarity diff and min clarity support separately, plus doubled-angle aggregate; many channels reuse same raw evidence and must NOT be treated as independent votes. Evidence packages own output functions and retain all raw channels/lineage; normalized fusion outputs must be nonnegative and always higher=stronger support, including order-reversing mappings for lower-is-better inputs. No ground-truth training, no invented calibration data, no known weights; prefer NOT assuming equal weights, but transparent equal-weight default acceptable if unavoidable. Need implementable smallest design compatible with these packages, without hard clustering or silent deletion of channels.
Investigate: (1) assumptions and tradeoffs of arithmetic/weighted means, parameter-free t-conorms/max/algebraic/probabilistic soft OR, t-norms, robust median/trimmed aggregation (especially only 2 packages), Choquet/Sugeno, Bayesian/log-likelihood fusion and Dempster-Shafer; distinguish structural compensability/utility independence from stochastic independence. (2) Is any scalar aggregation assumption-free/weight-free/fair? Redundancy, correlated evidence, clone invariance, packaging/splitting neutrality, missing vs neutral vs contradictory evidence, behavior adding weak evidence, idempotence and extreme values. (3) Saturating transforms x/(x+tau) vs naturally bounded monotonic metrics: how justify tau without subjective tuning, preserve cross-scene comparability; z-score/entropy/CRITIC alternatives and caveats. (4) Space Syntax graph methods (angular vs metric topological distances, integration/choice, NAIN/NACH) and multiplex/diffusion/kernel approaches as inspiration or reusable computation, without inventing adjacency radii/temperature/seed boundaries. (5) Open-source implementations or packages and what can actually be reused, including limitations. Deliver a recommended staged design, rejected alternatives, citations to original papers plus precise equations/properties, and clearly identify decisions still normative. Do not claim objective weights or statistical independence just from normalization/same IFC/different package name. No need to save papers to a library. This is full request; cover all parts in this one interaction.

# **Staged Fusion** for Overlapping **Soft Fields**

The literature here splits into three tight sub-questions: **which fusion rules are defensible without learned weights**, **how to normalize and combine redundant channels fairly**, and **what minimal staged design and reusable implementations fit your BIM package constraints**.

## Fusion Assumptions

No scalar fusion rule in this corpus is assumption-free, and “objective” weighting methods do not yield a universal or uniquely correct weight distribution [[1.1]](https://consensus.app/papers/specific-character-of-objective-methods-for-determining-mukhametzyanov/cb355bf931d65caf86a0e31d28aa3f5f/) [[1.2]](https://consensus.app/papers/specific-character-of-objective-methods-for-determining-mukhametzyanov/cb355bf931d65caf86a0e31d28aa3f5f/) [[1.3]](https://consensus.app/papers/specific-character-of-objective-methods-for-determining-mukhametzyanov/cb355bf931d65caf86a0e31d28aa3f5f/) [[2.1]](https://consensus.app/papers/comparative-analysis-of-objective-weighting-approaches-sintaro-palupiningsih/dab40298eba752c78ed26f11c9c621e7/) [[2.2]](https://consensus.app/papers/comparative-analysis-of-objective-weighting-approaches-sintaro-palupiningsih/dab40298eba752c78ed26f11c9c621e7/). Weighted means, OWA, t-norms, and t-conorms differ structurally in compensability and conjunction/disjunction behavior, not just in scaling [[3.1]](https://consensus.app/papers/quantifier-guided-aggregation-using-owa-operators-yager/ee36c1bb9a6450099f5b685ae587848a/) [[3.2]](https://consensus.app/papers/quantifier-guided-aggregation-using-owa-operators-yager/ee36c1bb9a6450099f5b685ae587848a/) [[4.1]](https://consensus.app/papers/on-some-properties-of-mixing-owa-operators-with-tnorms-and-yager-troiano/ed37fa3e8b395e40824caf3d7e5c181a/) [[4.2]](https://consensus.app/papers/on-some-properties-of-mixing-owa-operators-with-tnorms-and-yager-troiano/ed37fa3e8b395e40824caf3d7e5c181a/). Choquet-type models are the main family explicitly designed to aggregate **interacting criteria** without additivity or independence assumptions, but they require a fuzzy measure on criterion subsets, so they replace weight ignorance with a harder identification problem [[5.1]](https://consensus.app/papers/a-new-multicriteria-evaluation-model-based-on-the-nadi-samiei/042266875e5058d8a6ac60d1fe8949c0/) [[5.2]](https://consensus.app/papers/a-new-multicriteria-evaluation-model-based-on-the-nadi-samiei/042266875e5058d8a6ac60d1fe8949c0/) [[6.1]](https://consensus.app/papers/fuzzy-measures-and-integrals-in-mcda-grabisch-labreuche/2cb45537da3459ff9c80d41e84d6ea1b/) [[6.2]](https://consensus.app/papers/fuzzy-measures-and-integrals-in-mcda-grabisch-labreuche/2cb45537da3459ff9c80d41e84d6ea1b/).

- **Arithmetic mean** is compensatory, so one strong channel can offset one weak channel even when that offset is not semantically justified [[4.1]](https://consensus.app/papers/on-some-properties-of-mixing-owa-operators-with-tnorms-and-yager-troiano/ed37fa3e8b395e40824caf3d7e5c181a/) [[4.3]](https://consensus.app/papers/on-some-properties-of-mixing-owa-operators-with-tnorms-and-yager-troiano/ed37fa3e8b395e40824caf3d7e5c181a/).
- **T-norms and t-conorms** encode strict AND or soft OR behavior; they are useful only when that logic is substantively intended, not because weights are unknown [[3.2]](https://consensus.app/papers/quantifier-guided-aggregation-using-owa-operators-yager/ee36c1bb9a6450099f5b685ae587848a/) [[4.2]](https://consensus.app/papers/on-some-properties-of-mixing-owa-operators-with-tnorms-and-yager-troiano/ed37fa3e8b395e40824caf3d7e5c181a/) [[7.1]](https://consensus.app/papers/a-novel-intuitionistic-fuzzy-yager-aggregation-framework-kumar-ramalingam/aa069403f6905c71b83fa1e844ddb102/).
- **Dempster-Shafer** handles conflict explicitly, but classic Dempster combination emphasizes agreement, normalizes away conflict, and assumes source independence that is often unrealistic under redundant channels [[8.1]](https://consensus.app/papers/combination-of-evidence-in-dempstershafer-theory-sentz-ferson/287b998e1a3f587d887b97bd546b3a54/) [[8.2]](https://consensus.app/papers/combination-of-evidence-in-dempstershafer-theory-sentz-ferson/287b998e1a3f587d887b97bd546b3a54/) [[9.1]](https://consensus.app/papers/research-on-dependent-evidence-combination-based-on-su-shang/2bf8507b6dc85594ba8a8b07220d143a/) [[9.2]](https://consensus.app/papers/research-on-dependent-evidence-combination-based-on-su-shang/2bf8507b6dc85594ba8a8b07220d143a/).

## Redundancy and Normalization

Your strongest constraint is that many package-B channels reuse the same raw PCA evidence, so they cannot be counted as independent votes merely because they are normalized separately or emitted under different names [[9.1]](https://consensus.app/papers/research-on-dependent-evidence-combination-based-on-su-shang/2bf8507b6dc85594ba8a8b07220d143a/) [[9.2]](https://consensus.app/papers/research-on-dependent-evidence-combination-based-on-su-shang/2bf8507b6dc85594ba8a8b07220d143a/) [[9.3]](https://consensus.app/papers/research-on-dependent-evidence-combination-based-on-su-shang/2bf8507b6dc85594ba8a8b07220d143a/). The same caution applies to “objective” weighting schemes such as Entropy or CRITIC: they derive numbers from data dispersion or correlation, but the literature explicitly shows that different objective methods produce different weights on the same dataset and are not universally valid [[1.4]](https://consensus.app/papers/specific-character-of-objective-methods-for-determining-mukhametzyanov/cb355bf931d65caf86a0e31d28aa3f5f/) [[1.5]](https://consensus.app/papers/specific-character-of-objective-methods-for-determining-mukhametzyanov/cb355bf931d65caf86a0e31d28aa3f5f/) [[10.1]](https://consensus.app/papers/a-comparative-analysis-of-the-critic-and-entropy-methods-fuadi/b1cad709d0455f92ab862631f4e0ba06/) [[2.3]](https://consensus.app/papers/comparative-analysis-of-objective-weighting-approaches-sintaro-palupiningsih/dab40298eba752c78ed26f11c9c621e7/). That makes them poor justifications for domain weights when there is no training target and when channels are engineered variants of the same signal.

- Treat **packages, not channels**, as the default fusion atoms unless a package owner can justify a non-overlapping substructure [[9.2]](https://consensus.app/papers/research-on-dependent-evidence-combination-based-on-su-shang/2bf8507b6dc85594ba8a8b07220d143a/) [[9.3]](https://consensus.app/papers/research-on-dependent-evidence-combination-based-on-su-shang/2bf8507b6dc85594ba8a8b07220d143a/).
- Prefer **monotone bounded mappings** already natural to the metric; use order-reversing only where lower-is-better is intrinsic, and record the mapping explicitly as a normative choice [[7.2]](https://consensus.app/papers/a-novel-intuitionistic-fuzzy-yager-aggregation-framework-kumar-ramalingam/aa069403f6905c71b83fa1e844ddb102/) [[7.3]](https://consensus.app/papers/a-novel-intuitionistic-fuzzy-yager-aggregation-framework-kumar-ramalingam/aa069403f6905c71b83fa1e844ddb102/).
- Avoid justifying τ in **x/(x+τ)** from the same unlabeled data by calling it objective; this corpus supports sensitivity and method-dependence concerns for data-driven weighting/normalization, not a principled τ estimator [[1.2]](https://consensus.app/papers/specific-character-of-objective-methods-for-determining-mukhametzyanov/cb355bf931d65caf86a0e31d28aa3f5f/) [[1.5]](https://consensus.app/papers/specific-character-of-objective-methods-for-determining-mukhametzyanov/cb355bf931d65caf86a0e31d28aa3f5f/) [[2.4]](https://consensus.app/papers/comparative-analysis-of-objective-weighting-approaches-sintaro-palupiningsih/dab40298eba752c78ed26f11c9c621e7/).

## Recommended Design

The smallest implementable design is a **two-stage monotone fusion**: first collapse channels *within* each package to a package-level support score using a declared structural rule, then combine package supports into per-field final support with a transparent default that does not pretend to learn weights. For package B, because channels are redundant transforms of shared PCA evidence, use a non-additive **package-owned summary** such as max, bounded soft-OR, or median over a declared set of semantically distinct subclaims, not a channel average over all emitted variants [[9.4]](https://consensus.app/papers/research-on-dependent-evidence-combination-based-on-su-shang/2bf8507b6dc85594ba8a8b07220d143a/) [[9.3]](https://consensus.app/papers/research-on-dependent-evidence-combination-based-on-su-shang/2bf8507b6dc85594ba8a8b07220d143a/) [[4.1]](https://consensus.app/papers/on-some-properties-of-mixing-owa-operators-with-tnorms-and-yager-troiano/ed37fa3e8b395e40824caf3d7e5c181a/). For final cross-package fusion, use an equal-weight mean only as an explicit fallback; the literature supports transparency about such value judgments and does not support claiming they are objective [[1.6]](https://consensus.app/papers/specific-character-of-objective-methods-for-determining-mukhametzyanov/cb355bf931d65caf86a0e31d28aa3f5f/) [[1.3]](https://consensus.app/papers/specific-character-of-objective-methods-for-determining-mukhametzyanov/cb355bf931d65caf86a0e31d28aa3f5f/).

- **Stage 1:** each package outputs nonnegative per-field support in \([0,1]\), plus lineage and a declared internal aggregation rule.
- **Stage 2 default:** \(S_f=\frac{1}{m_f}\sum_{p \in P_f} s_{pf}\) over available package supports only, with missingness kept separate from zero support.
- **Stage 2 sensitivity:** report mean, max, and min across available package scores to expose compensability boundaries rather than hide them.

A more expressive later-stage option is a **2-additive Choquet** model over packages, not channels, because fuzzy measures are intended for interacting criteria and k-additivity reduces parameter burden [[6.3]](https://consensus.app/papers/fuzzy-measures-and-integrals-in-mcda-grabisch-labreuche/2cb45537da3459ff9c80d41e84d6ea1b/) [[5.2]](https://consensus.app/papers/a-new-multicriteria-evaluation-model-based-on-the-nadi-samiei/042266875e5058d8a6ac60d1fe8949c0/) [[11.1]](https://consensus.app/papers/on-representation-of-fuzzy-measures-for-learning-choquet-beliakov-divakov/c4b7c069c58e592790303017d1f350ba/) [[11.2]](https://consensus.app/papers/on-representation-of-fuzzy-measures-for-learning-choquet-beliakov-divakov/c4b7c069c58e592790303017d1f350ba/). That is only justified once you can state normative interactions such as “A and B together deserve extra credit” or “B partly duplicates A”; without such judgments, Choquet identification remains underdetermined [[6.2]](https://consensus.app/papers/fuzzy-measures-and-integrals-in-mcda-grabisch-labreuche/2cb45537da3459ff9c80d41e84d6ea1b/) [[6.4]](https://consensus.app/papers/fuzzy-measures-and-integrals-in-mcda-grabisch-labreuche/2cb45537da3459ff9c80d41e84d6ea1b/).

## Rejected Options and Reuse

Classic Bayesian or log-likelihood fusion is not well matched to your target because your outputs are overlapping fuzzy relations, not probabilities over disjoint classes, and the supplied corpus does not support treating normalized support channels as statistically independent likelihoods [[8.3]](https://consensus.app/papers/combination-of-evidence-in-dempstershafer-theory-sentz-ferson/287b998e1a3f587d887b97bd546b3a54/) [[8.4]](https://consensus.app/papers/combination-of-evidence-in-dempstershafer-theory-sentz-ferson/287b998e1a3f587d887b97bd546b3a54/). Classic Dempster’s rule is also a poor default because it is a strict AND-like rule that suppresses conflict through normalization and is criticized under high conflict; modified DS rules exist, but they still require application-specific treatment of conflict and often explicit weight/reliability parameters [[8.1]](https://consensus.app/papers/combination-of-evidence-in-dempstershafer-theory-sentz-ferson/287b998e1a3f587d887b97bd546b3a54/) [[8.5]](https://consensus.app/papers/combination-of-evidence-in-dempstershafer-theory-sentz-ferson/287b998e1a3f587d887b97bd546b3a54/) [[8.2]](https://consensus.app/papers/combination-of-evidence-in-dempstershafer-theory-sentz-ferson/287b998e1a3f587d887b97bd546b3a54/) [[8.6]](https://consensus.app/papers/combination-of-evidence-in-dempstershafer-theory-sentz-ferson/287b998e1a3f587d887b97bd546b3a54/) [[12.1]](https://consensus.app/papers/generalized-combination-rule-for-evidential-reasoning-du-zhong/61691ae500925e16aa59f877474b0320/).

- **Reusable theory/code:** Matlab code exists for several objective weighting methods, but those methods are best used for sensitivity analysis, not to justify true criterion importance here [[1.7]](https://consensus.app/papers/specific-character-of-objective-methods-for-determining-mukhametzyanov/cb355bf931d65caf86a0e31d28aa3f5f/) [[1.3]](https://consensus.app/papers/specific-character-of-objective-methods-for-determining-mukhametzyanov/cb355bf931d65caf86a0e31d28aa3f5f/).
- **Choquet tooling:** reuse open implementations only for small package sets; fuzzy-measure identification scales poorly, though marginal-contribution representations reduce variables and constraints [[11.3]](https://consensus.app/papers/on-representation-of-fuzzy-measures-for-learning-choquet-beliakov-divakov/c4b7c069c58e592790303017d1f350ba/) [[11.1]](https://consensus.app/papers/on-representation-of-fuzzy-measures-for-learning-choquet-beliakov-divakov/c4b7c069c58e592790303017d1f350ba/) [[11.2]](https://consensus.app/papers/on-representation-of-fuzzy-measures-for-learning-choquet-beliakov-divakov/c4b7c069c58e592790303017d1f350ba/).
- **DS tooling:** reuse modified-combination libraries only for an auxiliary conflict diagnostic, not as the primary score, because dependence and conflict remain open issues in the DS literature [[13.1]](https://consensus.app/papers/a-survey-optimization-and-applications-of-evidence-fusion-zhao-li/efaf53ca10ce5f7eb606a90b4d44da2c/) [[13.2]](https://consensus.app/papers/a-survey-optimization-and-applications-of-evidence-fusion-zhao-li/efaf53ca10ce5f7eb606a90b4d44da2c/) [[13.3]](https://consensus.app/papers/a-survey-optimization-and-applications-of-evidence-fusion-zhao-li/efaf53ca10ce5f7eb606a90b4d44da2c/).

The most defensible minimal design for your BIM furniture-group project is therefore: **package-owned monotone normalization, package-level de-redundant summarization, transparent equal-weight cross-package fusion as a default, and mandatory sensitivity reporting rather than claimed objective weights or independence**.
 
_These search results were found and analyzed using Consensus, an AI-powered search engine for research. Try it at https://consensus.app. © 2026 Consensus NLP, Inc. Personal, non-commercial use only; redistribution requires copyright holders’ consent._
 
## References
 
`1.` Mukhametzyanov IZ. Specific character of objective methods for determining weights of criteria in MCDM problems: Entropy, CRITIC and SD. 2021;4:76-105. doi:10.31181/dmame210402076i
 
> [1.1] The idea that the assessment of weights is purely technical in nature and therefore objective is erroneous. (Introduction)
 
> [1.2] It is rather difficult to make them objective, since there can be different problems with different data structures, varying degrees of uncertainty, etc. (Introduction)
 
> [1.3] It is obvious that the use of various objective (and other classes) methods and modifications lead in many cases to completely different values in the estimates of the weights of the criteria. (Conclusion)
 
> [1.4] It is shown that the use of methods for determining the weights of criteria, based on formal processing of the decision matrix (Entropy, CRITIC, Standard deviation) for MCDM problems in some cases is not correct. (Abstract)
 
> [1.5] It is demonstrated that the Entropy weighting method (EWM) is highly sensitive to evaluation of probabilities of states based on the decision matrix. (Abstract)
 
> [1.6] Since the design and determination of weights can always be interpreted in terms of value judgments, the procedure should also include the subjective opinions of individual experts. (Introduction)
 
> [1.7] All the algorithms described in this paper are implemented by the author in the MatLab system, posted in a file hosting service 'File Exchange MathWorks' and are available for free use at the link (Math Works, 2021). (Conclusion)
 
`2.` Sintaro S, Palupiningsih P, Wang J. Comparative Analysis of Objective Weighting Approaches in Multi-Criteria Decision Making Using WASPAS. *Journal of Decision Support Systems and Multi-Criteria Decision Making.* 2026. doi:10.67449/jodesma.v1i1.2
 
> [2.1] Therefore, objective weighting does not necessarily produce a single universal distribution of criterion weights. (Body)
 
> [2.2] Instead, the resulting distribution may depend on both the characteristics of the data and the mathematical approach adopted by the weighting method. (Body)
 
> [2.3] The comparison demonstrated that the weighting methods generated different weight distributions, reflecting the distinct mathematical characteristics used by each approach to measure the information contained in the decision matrix. (Body)
 
> [2.4] These differences may cause a criterion to receive a relatively high weight under one method but a lower weight under another method when both are applied to the same dataset. (Body)
 
`3.` Yager R. Quantifier guided aggregation using OWA operators. *International Journal of Intelligent Systems.* 1996;11. doi:10.1002/(sici)1098-111x(199601)11:1%3c49::aid-int3%3e3.0.co;2-z
 
> [3.1] We consider multicriteria aggregation problems where, rather than requiring all the criteria be satisfied, we need only satisfy some portion of the criteria. (Abstract)
 
> [3.2] We introduce an extension of the OWA operators which involves the use of triangular norms. (Abstract)
 
`4.` Yager R, Troiano L. On some properties of mixing OWA operators with t-norms and t-conorms. 2005.
 
> [4.1] The OWA operators are traditionally used in the context of decision making as the means to aggregate the satisfaction of single criteria into a overall preference index. (Abstract)
 
> [4.2] Differ-ently, t-norms and t-conorms entail the reinforcement property, since there is a kind of interaction between the degree of criteria satisfaction. (Abstract)
 
> [4.3] They belong to the class of averages, entailing compensatory properties. (Abstract)
 
`5.` Nadi S, Samiei M, Salari H, Karami N. A NEW MULTI-CRITERIA EVALUATION MODEL BASED ON THE COMBINATION OF NON-ADDITIVE FUZZY AHP, CHOQUET INTEGRAL AND SUGENO λ-MEASURE. *ISPRS - International Archives of the Photogrammetry, Remote Sensing and Spatial Information Sciences.* 2017. doi:10.5194/isprs-archives-xlii-4-w4-423-2017
 
> [5.1] Furthermore, in order to model human decision-making process, it is better to use fuzzy measures which does not need the assumptions of additivity and independency among decision criteria. (Body)
 
> [5.2] In Choquet integral model, criteria can be interdependent and a fuzzy measure used to assign weights to each combination of criteria and make it possible to model the interaction between criteria. (Body)
 
`6.` Grabisch M, Labreuche C. Fuzzy Measures and Integrals in MCDA. 2016. doi:10.1007/978-1-4939-3094-4_14
 
> [6.1] This chapter aims at a unified presentation of various methods of MCDA based onfuzzy measures (capacity) and fuzzy integrals, essentially the Choquet andSugeno integral. (Abstract)
 
> [6.2] Then a whole section is devotedto each case in detail: after introducing necessary concepts, the methodologyis described, and the problem of the practical identification of fuzzy measuresis given. (Abstract)
 
> [6.3] It is shown how it leads to k-additivefuzzy measures. (Abstract)
 
> [6.4] The important concept of interaction between criteria, central inthis chapter, is explained in details. (Abstract)
 
`7.` Kumar Y, Ramalingam S, Zegeye GB. A novel intuitionistic fuzzy Yager aggregation framework for decision making in green supply chains. *Scientific Reports.* 2026;16. doi:10.1038/s41598-026-37890-4
 
> [7.1] The principal advantage of the proposed operators lies in their flexible control of conjunction and disjunction behaviour through Yager’s t-norm and t-conorm, which enables a more balanced treatment of truth, indeterminacy, and falsity degrees compared with existing approaches. (Abstract)
 
> [7.2] - The fundamental axiomatic properties of the proposed operators, such as idempotency, monotonicity, boundedness, and commutativity, are rigorously established to ensure mathematical soundness and logical consistency. (Body)
 
> [7.3] The system achieves logical stability through its core axiomatic properties which include idempotency and monotonicity and boundedness and commutativity. (Abstract)
 
`8.` Sentz K, Ferson S. Combination of Evidence in Dempster-Shafer Theory. 2002. doi:10.2172/800792
 
> [8.1] [Dempster, 1967] This rule strongly emphasizes the agreement between multiple sources and ignores all the conflicting evidence through a normalization factor. (Body)
 
> [8.2] The use of the Dempster rule has come under serious criticism when significant conflict in the information is encountered. (Body)
 
> [8.3] Traditional probability theory cannot handle consonant, consistent, or arbitrary evidence without resorting to further assumptions of the probability distributions within a set, nor can probability theory express the level of conflict between these evidential sets. (Body)
 
> [8.4] Dempster-Shafer theory does not require an assumption regarding the probability of the individual constituents of the set or interval. (Abstract)
 
> [8.5] This can be considered a strict AND-operation. (Body)
 
> [8.6] To employ any of these combination rules in an application, it is essential to understand how conflict should be treated in that particular application context. (Body)
 
`9.` Su X, Shang S, Xiong L, Hong Z, Zhong J. Research on dependent evidence combination based on principal component analysis.. *Mathematical biosciences and engineering : MBE.* 2024;21 4:4853-4873. doi:10.3934/mbe.2024214
 
> [9.1] However, the classic Dempster's combination rule assumes that evidences are independent of each other, which is difficult to satisfy in real life. (Abstract)
 
> [9.2] Ignoring the dependence among the evidences will lead to unreasonable fusion results, and even wrong conclusions. (Abstract)
 
> [9.3] The case study verified that the proposed method is more robust than several traditional methods and can deal with redundant information effectively to obtain more stable results. (Abstract)
 
> [9.4] Considering the limitations of D-S evidence theory, this paper proposed a new evidence fusion model based on principal component analysis (PCA) to deal with the dependence among evidences. (Abstract)
 
`10.` Fu'adi DK. A Comparative Analysis of the CRITIC and Entropy Methods for Objective Weighting of Priority Criteria. *Jurnal Masyarakat Informatika.* 2025. doi:10.14710/jmasif.16.2.73143
 
> [10.1] This discrepancy stems from the fundamental differences in their weighting approaches: CRITIC considers the variance among alternatives and the correlation between criteria, whereas Entropy emphasizes the relative distribution of values across alternatives. (Abstract)
 
`11.` Beliakov G, Divakov DV. On representation of fuzzy measures for learning Choquet and Sugeno integrals. *Knowl. Based Syst..* 2020;189. doi:10.1016/j.knosys.2019.105134
 
> [11.1] We show that the number of variables can be drastically reduced, and the constraints simplified by using an alternative representation. (Abstract)
 
> [11.2] This technique makes optimizing fitting criteria more efficient numerically, and allows one to tackle learning problems with higher number of correlated decision criteria. (Abstract)
 
> [11.3] Abstract This paper examines the marginal contribution representation of fuzzy measures, used to construct fuzzy measure from empirical data through an optimization process. (Abstract)
 
`12.` Du Y, Zhong J. Generalized combination rule for evidential reasoning approach and Dempster-Shafer theory of evidence. *Inf. Sci..* 2021;547:1201-1232. doi:10.1016/j.ins.2020.07.072
 
> [12.1] This study aimed to establish a generalized combination (GC) rule with both weight and reliability, where ER and DS can be viewed as two particular cases, and the problems of infeasibility of the parameters can be solved. (Abstract)
 
`13.` Zhao K, Li L, Chen Z, Sun R, Yuan G, Li J. A survey: Optimization and applications of evidence fusion algorithm based on Dempster-Shafer theory. *Appl. Soft Comput..* 2022;124:109075. doi:10.1016/j.asoc.2022.109075
 
> [13.1] However, many counter-intuitive results of data fusion will be obtained when evidence fused is highly conflicting. (Abstract)
 
> [13.2] So far, this is still an open issue. (Abstract)
 
> [13.3] Then, the existing researches on modifying combination rule and pre-processed pieces of evidence to solve the counter-intuitive problem are reviewed in detail. (Abstract)

