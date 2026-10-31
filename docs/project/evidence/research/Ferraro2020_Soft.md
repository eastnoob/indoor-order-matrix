Received: 5 February 2019 

Revised: 10 May 2019 

Accepted: 10 May 2019 

DOI: 10.1002/wics.1480 

#### A D V A N C E D R E V I E W 

# Soft clustering 

## Maria Brigida Ferraro | Paolo Giordani 

Department of Statistical Sciences, Sapienza University of Rome, Rome, Italy 

##### Correspondence 

Maria Brigida Ferraro, Department of Statistical Sciences, Sapienza University of Rome, Rome, Italy. Email: mariabrigida.ferraro@uniroma1.it 

### Abstract 

Clustering is one of the most used tools in data analysis. In the last decades, due to the increasing complexity of data, soft clustering has received a great deal of attention. There exist different approaches that can be considered as soft. The most known is the fuzzy approach that consists in assigning objects to clusters with membership degrees, depending on the dissimilarities between each object and all the prototypes, ranging in the unit interval. Closely related to the fuzzy approach, there is the possibilistic one that, differently from the previous one, relaxes some constraints on the membership degrees. In particular, the objects are assigned to clusters with degrees of typicalities, depending just on the dissimilarities between each object and the closest prototype. A further soft approach is the rough one. In this case, there are not degrees ranging between 0 and 1 but objects with intermediate features belong to the boundary region and are assigned to more than one cluster. Even if it is not universally recognized in the scientific community as an approach of soft clustering, from our point of view, the model-based approach can also be considered as such. Model-based clustering methods also produce a soft partition of the objects and the posterior probability of a component membership may play a role similar to the membership degree. The four approaches are critically described from a theoretical point of view and an empirical comparative analysis is carried out. 

This article is categorized under: 

- Statistical Learning and Exploratory Methods of the Data Sciences > Clustering and Classification 

Statistical and Graphical Methods of Data Analysis > Multivariate Analysis Statistical Learning and Exploratory Methods of the Data Sciences > Exploratory Data Analysis 

K E Y W O R D S 

fuzzy approach, model-based approach, possibilistic approach, rough approach, soft clustering 

## 1 | INTRODUCTION 

Cluster analysis aims at determining a small number k of homogeneous groups (clusters) from a set of n objects according to a given dissimilarity measure based on p observed variables X1, … , Xp. See, for an overview, (Hennig, Meila, Murtagh, & Rocci, 2015). In many practical applications, there exist objects that have intermediate characteristics among clusters, hence 

© 2019 Wiley Periodicals, Inc. 1 of 12 

wires.wiley.com/compstats 

WIREs Comput Stat. 2019;e1480. 

https://doi.org/10.1002/wics.1480 

2 of 12 

FERRARO AND GIORDANI 

they cannot be clearly assigned. In these cases, the classical (hard) approach to clustering leads to an unrealistic assignment and the objects are forced to belong to just one cluster. The soft approach arises to overcome this drawback. The main idea is that each data point can belong to more than one cluster. There exist at least four types of soft clustering approaches: fuzzy, possibilistic, rough, and model-based. 

Fuzzy clustering consists in assigning the data points to the clusters according to a certain degree, called membership degree and ranging from 0 (complete nonmembership) to 1 (complete membership). The membership degree is also known as a degree of sharing since its computation involves the ratio of the dissimilarity between each object and the closest prototype to the sum of the dissimilarities between each object and all the prototypes. Klawonn, Kruse, and Winkler (2015) have demonstrated that the use of the membership degrees is very important from a computational point of view, even if in some situations it is not necessary from a theoretical point of view. In fact, in the literature, starting from the most known fuzzy clustering algorithm, the fuzzy k-means (FkM) (Bezdek, 1981), a large number of new fuzzy clustering algorithms have been introduced without having their counterparts in a classical/crisp setting, for example, the Gustafson-Kessel FkM (Gustafson & Kessel, 1978), the FkM with the entropic regularization (R. P. Li & Mukaidono, 1995, 1999), and the FkM with the polynomial fuzzifiers (Klawonn et al., 2015). 

The possibilistic approach consists in relaxing the unit-sum constraints of the membership degrees, by adding a penalization term. This leads to membership degrees that can be interpreted as degrees of compatibility of the objects to the clusters and objects that are far from all the prototypes are assigned to the clusters with lower membership degrees (close to 0). Starting from the original possibilistic k-means (PkM) algorithm (Krishnapuram & Keller, 1993), numerous extensions have been proposed. Refer, for instance, to Ménard, Courboulay, and Pierre-André (2003), Timm, Borgelt, Doring, and Kruse (2004), and Yang and Wu (2006). 

The third approach is based on the notion of rough set, proposed by Pawlak (1982, 1992). It is possible to define each rough set using its lower and upper approximations (UAs). Based on the distances between each object and each prototype, it can be stated whether a data point belong to a lower approximation (LA) or to two or more UAs or boundary regions. The most know algorithm is the rough k-means (RkM). There exist different extensions in the literature. 

Most researchers think that only the three above described approaches can be considered to be soft. From our point of view, however, the model-based one can also be considered as soft clustering. Model-based clustering methods produce a soft partition of the objects as well and the posterior probability to belong to a component/cluster plays a role similar to that of the membership degree. Starting from the most used model, the mixture of Gaussian densities (Fraley & Raftery, 2002), extensions involving different parametric distributions have been proposed. In particular, in case of outliers, it is often adopted a mixture of t-distributions (Peel & McLachlan, 2000). For an overview on model-based clustering, see McLachlan and Peel (2000a). 

## 2 | FUZZY CLUSTERING 

In fuzzy clustering data points are assigned to the clusters according to a membership degree. A degree close to 1 implies that the object is similar to the prototype, while a value close to 0 indicates the complete nonmembership of the object to the clusters, so it is far from the corresponding prototype. Starting from the extension of the classical k-Means (kM) (MacQueen, 1967) to the fuzzy case, the FkM (Bezdek, 1981), a large number of new fuzzy clustering algorithms have been introduced. See, for example, de Oliveira and Pedrycz (2007). 

## 2.1 | Fuzzy k-means 

The most known and used fuzzy clustering algorithm is the FkM. It aims at determining a fuzzy partition of n objects into k clusters by solving the following minimization problem: 





3 of 12 

FERRARO AND GIORDANI 

where d(�, �) is the Euclidean distance. xi = [xi1, ���, xip] (i = 1, … , n) is the generic row of the data matrix X of order (n × p). In (1) U is the membership degree matrix of order (n × k), whose generic element uig represents the degree of membership of object i to cluster g. The row sums of U are equal to 1. H is the prototype (centroid) matrix of order (k × p), whose generic row is hg = [hg1, ���, hgp] (g = 1, … , k). Finally, m > 1 is the parameter of fuzziness, usually fixed between 1.5 and 2. 

The solution of (1) is obtained by means of an iterative algorithm. In detail, the Lagrangian multiplier (λ) method is adopted, by setting the partial derivatives of the Lagrangian function (L) w.r.t. uig and λ equal to 0. Note that only the latter constraint in 2 is used, since the former one is automatically fulfilled. Then, fixing uig, we obtain hg by setting equal to 0 the partial derivatives of L w.r.t. hg. The iterative solution is: 



As we can see, the membership degrees of the objects to the clusters are such that they are inversely related to the relative dissimilarities between the objects and the centroids. For this reason, the membership degrees can be interpreted as degrees of sharing (of the observations to the clusters). 

There exist several extensions in the literature. Since, the parameter m has not a realistic meaning, the FkM with an entropic regularization (R. P. Li & Mukaidono, 1995, 1999) can be considered. The degree of fuzzy entropy represents the “temperature” in statistical physics. In order to recognize also nonspherical clusters, the FkM with covariance matrices has been introduced by Gustafson and Kessel (1978) and the entropic version by Ferraro and Giordani (2013). Klawonn and Höppner (2003) propose the FkM with a polynomial fuzzifier to overcome the drawback of assigning objects to all the clusters with nonzero membership degrees. As for the classical k-means type methods, the performance of all the above fuzzy algorithms is affected by the outliers. The problem is due to the unit-sum constraints of the membership degrees. It implies that also the anomalous objects are assigned to the clusters and the centroids are affected by these points. A timid kind of robustification is given by the fuzzy k-medoids (FkMed) algorithm (Krishnapuram, Joshi, Nasraoui, & Yi, 2001), a generalization of the classical k-medoids (Kaufman & Rousseuw, 1990). Another robust proposal is due to Davé (1991) with the introduction of the so called noise cluster that is an additional cluster (not a proper cluster) containing all the objects considered as outliers. The noise prototype is a universal entity such that it is always at the same distance from every point in the dataset. 

A separate mention deserves proposals in Masson and Denoeux (2008, 2009); Antoine, Quost, Masson, and Denoeux (2012), consisting in evidential version of fuzzy clustering algorithms. 

Furthermore, in case of relational data, there exist different proposals: relational dual of fuzzy c-means (RFCM) and nonEuclidean RFCM (NERFCM) (Hathaway, Devenport, & Bezdek, 1988), FANNY (Kaufman & Rousseuw, 1990), fuzzy relational clustering (FRC), that is an extension of FANNY, an non-Euclidean fuzzy relational clustering (NE-FRC) (Davé & Sen, 2002). 

## 3 | POSSIBILISTIC CLUSTERING 

As already discussed in the previous section, the FkM and its extensions may lead to anomalous results in the presence of possible outliers. To overcome this drawback, despite the FkMed and the fuzzy clustering algorithms with noise cluster, the possibilistic approach can be used (Krishnapuram & Keller, 1993). It consists in relaxing the unit-sum constraints of the membership degrees, by adding a penalization term. This leads to membership degrees that can be interpreted as degrees of compatibility of the objects to the clusters and objects that are far from all the prototypes are assigned to the clusters with lower membership degrees (close to 0). Starting from the original PkM algorithm (Krishnapuram & Keller, 1993), numerous extensions have been proposed. Refer to Ménard et al. (2003), Timm et al. (2004), Yang and Wu (2006), for instance. 

## 3.1 | Possibilistic k-means 

The most known possibilistic clustering algorithm is the PkM clustering method that can be formalized as 

4 of 12 

FERRARO AND GIORDANI 





where tig is the membership degree of observation i to cluster g, stored in the matrix T of order (n × k). The membership degrees are possibility values and are usually referred to as the degrees of typicality (of the observations to the clusters). They are the possibilistic variant of the membership degrees in FkM and are used to recognize the soft partition. The parameter γg is cluster-specific and it tunes the importance of the clusters and η (>1) is the fuzzifier. The parameter γg can be defined as 



where, usually, γ = 1 and hg’s and uig's are obtained from FkM. Equation (5) can be motivated by noting that the γg's give the relative weight of the second term of the loss compared to the first one. The second term avoids the trivial solution with T = 0. 

The solution of PkM, derived by using an iterative algorithm, is 



In PkM, the degrees of typicality, tig's, are inversely related to the dissimilarities between the observations and the centroids. In fact, a common property of clustering methods based on the possibilistic approach is that the membership degrees are computed by considering only the dissimilarity between the observation and the closest centroid, regardless of the centroids of the remaining clusters. This explains how this approach manages contaminated data. Outliers are far from the bulk of the data and, thus, far from all the centroids. Therefore, they usually have degrees of typicality close to 0 to all the clusters (see, for a deeper discussion, Krishnapuram & Keller, 1993). 

Unfortunately, the PkM may suffer from the risk of coincident clusters (see the discussion in Barni, Cappellini, and Mecocci (1996) and in Krishnapuram and Keller (1996)). This limitation is due to the sum of the degrees of typicality for every observation to all the clusters that is no longer required to be equal to one. In addition, we can note that the optimization function in (3) can be decomposed into the sum of k terms that can be minimized independently of each other. A heuristic remedy to the coincident cluster problem is the use of a rational starting point. For instance, the iterative algorithm of PkM can be run starting from the FkM solution. A further approach to overcome the coincident clustering problem consists in adding a repulsion term among centroids in the loss function. Such a repulsion term forces the centroids to be far from each other (Timm et al., 2004). Besides, in Timm et al. (2004), a possibilistic Gustafson-Kessel algorithm is also provided. Moreover, in Yang and Wu (2006), a possibilistic clustering algorithm based on the FkM objective function, the partition coefficient and the partition entropy validity indices are introduced. 

In the literature, there exist also hybridizations of the fuzzy and the possibilistic approach: the fuzzy-possibilistic k-means (FPkM) (Pal, Pal, & Bezdek, 1997) and the possibilistic fuzzy k-means (PFkM) (Pal, Pal, Keller, & Bezdek, 2005). In the first one, the sum of the typicalities to a cluster over all the data is constrained to be equal to 1. This leads to unrealistic typicality values for large datasets. The PFkM avoids this limitation. Both FPkM and PFkM minimization problems are based on a linear combination of those of FkM and PkM. The importance of the two components, degrees of sharing for FkM and degrees of tipicality for PkM, is tuned by two weights. It follows that the potentialities of both methods are exploited and the drawbacks are overcome. In particular, the fuzzy component is used to assign the data to the closest prototype and it is useful to avoid the coincident cluster problem that may occur in PkM. On the other hand, the possibilistic component helps to detect outliers. A further hybridization is introduced in Yiming, Xianghui, and Pedrycz (2019): a new possibilistic fuzzy clustering with highdensity viewpoint driven by data and knowledge. Finally, in Ménard et al. (2003), a possibilistic and probabilistic fuzzy clustering algorithm is addressed. 

5 of 12 

FERRARO AND GIORDANI 

## 4 | ROUGH CLUSTERING 

The rough clustering methods are based on the notion of rough set proposed by Pawlak (1982, 1992). A rough set Cg is defined by means of its lower and UAs, <u>A�Cg�</u> and A�Cg�. The family of LA and UA of Cg must fulfill the following properties: 

- (P1)An object xi can be part of at most one LA. 

- (P2) xi 2 <u>A�Cg�</u> ) xi 2 A�Cg� 

- (P3) xi is not part of any LA , xi belongs to two or more UAs. 

The aim of rough clustering is to determine whether an object belongs to the UAs or LAs of a cluster. For each object vector, xi, in order to establish the assignment of xi, given a threshold ψ, the ratios d(xi, cg)/d(xi, cg<sup>0</sup> ), g = 1, … , k and g<sup>0</sup> = 1, … , k, are used. 

1. If d(xi, hg) is the minimum for 1 ≤ g ≤ k and d(xi, hg)/d(xi, hg<sup>0</sup> ) ≥ ψ for any pair (g, g<sup>0</sup> ) then xi 2 A�Cg� and xi 2 A�Cg0�. Furthermore, xi is not part of any LA. In this way property (P3) is fulfilled. 

2. Otherwise, xi 2 <u>A�Cg�</u> such that d(xi, hg) is the minimum for 1 ≤ g ≤ k. In addition, by property (P2), xi 2 A�Cg�. It follows that also in this case property (P1) is satisfied. 

## 4.1 | Rough k-means 

In RkM (Lingras & West, 2004), a cluster is described by two hard approximations, an LA and a UA (or boundary region). Hence, a data point has two bivalent membership degrees to cluster g, one for its LA and one for its UA: 



Objects in the LA surely belong to the corresponding cluster, while objects in the UA may belong to the cluster. The RkM can be considered as a soft method due to the boundary region for handling the uncertainty in the clustering process. In RkM clustering, the data points are assigned to either LA or UA using criteria [1] or [2]. The LA and UA are used to define the soft partition of the data, hence, they play the same role of the ones of the uig's in FkM and the tig<sup>0</sup> s in PkM. The centroids are computed as follows. If the cardinalities of <u>A�cg�</u> and A�cg� −A�cg� (denoted by j <u>A�cg�</u> j and j A�cg� −A�cg� j, respectively) are not equal to 0, then 



− with wl > 0 and wu > 0 such that wl + wu = 1 (usually wl > wu). If j <u>A�cg�</u> j6¼ 0 and j A�cg� <u>A�cg�</u> j = 0, then 







The algorithm proposed in Lingras and West (2004) was refined in Peters (2005, 2006) w.r.t. the objective function, the numerical stability and the stability of the clusters. 

In Mitra (2004), an evolutionary RkM clustering algorithm is proposed. It consists in using genetic algorithms for tuning the threshold. A rough k-medoids clustering algorithm is due to Peters and Lampart (2006), while the evolutionary version is 

6 of 12 

FERRARO AND GIORDANI 

due to Peters, Lampart, and Weber (2008). A further extension based on self-organizing maps is proposed in Lingras (2007), while in Peters, Weber, and Nowatzke (2012), a dynamic rough clustering is addressed. Chen and Miao (2011) propose an interval set clustering based on decision theory and F. Li, Ye, and Chen (2014) suggest an extended RkM algorithm based on the concepts of decision-theoretic rough set model. In Peters (2014), a refined RkM algorithm, utilizing Laplace's principle of indifference to calculate the means, is introduced. In addition, hybridizations of the fuzzy and rough approach are addressed in Mitra, Banka, and Pedrycz (2006) and in Mitra, Pedrycz, and Barman (2010). Mitra et al. (2006) propose to combine fuzzy and rough sets, by introducing the fuzzy LA and the fuzzy boundary for each cluster. In the rough-fuzzy k-means introduced by Mitra et al. (2010), the fuzzy membership degrees are used to deal with overlapping among clusters while the (crisp) lower and UAs of the rough sets are needed to define each cluster, besides the centroid. Maji and Pal (2007) introduce instead a rough-fuzzy k-medoids algorithm. A different kind of hybridization is due to Ferone and Maratea (2019). Their proposal consists in integrating the rough set principles in the graded possibilistic clustering. 

For further details, see the reviews in Peters and Lingras (2011); Peters, Crespo, Lingras, and Weber (2013); and Peters (2015a). 

## 5 | MODEL-BASED CLUSTERING 

In the model-based approach, clustering methods assume that the data are generated by a random statistical model and try to recover it from the data. In this context, the data follow a mixture distribution. Given x = (x1, x2, … , xn) 2 R<sup>p</sup> , the random vector xi is assumed to arise from a finite mixture of probability density functions: 



where πg, g = 1, … , k, such that πg > 0 and<sup>Pk</sup> g = 1<sup>πg = 1, are the mixing proportions, k is the number of components, f</sup> �<sup>xjθg</sup> � is the component density (g = 1, … , k), and Φ = ðπ1, ���, πk,θ1, ���,θkÞ is the parameter vector (McLachlan & Krishnan, 2008). Each mixture component density belongs to a specific parametric class and represents a cluster. Even thought it is not necessary that each mixture component density arises from the same parametric distribution family, we will focus only on the case where the parametric distribution family is the same for each mixture component. This is the most common case investigated in the literature. 

Parameter estimation is performed by the maximum likelihood approach. In detail, the estimation of the model parameters in Φ is done by applying the Expectation–Maximization (EM) algorithm (Dempster, Laird, & Rubin, 1977). Once the EM algorithm reaches the convergence, the soft partition of the data can be obtained by means of the posterior probabilities, by using the maximum a posteriori rule, that is, by assigning each data point to the cluster with the highest posterior probability. The posterior probabilities, as the membership degrees in the FkM algorithm, the degrees of typicalities in the PkM and the lower and UAs in the RkM, are used to determine the softness of the partition. 

## 5.1 | Finite mixtures of Gaussian densities 

The most used model for clustering is the Gaussian mixture distribution, that is, f �xijzig = 1, θg�eN�μg, Σg� (Fraley & Raftery, 2002). The finite mixture of Gaussian (FMG) densities is then given by 



where Φ = �π1, ���, πg− 1, μ1, ���,μg, Σ1, ���, Σg� denotes the parameter set for the finite mixture model and ϕ�xijμg, Σg� the underlying component-specific density function with parameters μg, Σg, g = 1, …, k. 

Therefore, ellipsoidal clusters centred at the mean vector μg are generated by the model in (10). The parameter Σg controls the other geometrical properties of each cluster. Parsimonious parametrizations of the cluster covariance matrices can be obtained through the eigen-decomposition Σg = λgDgAgD<sup>></sup> g<sup>(Banfield&Raftery,1993;Celeux&Govaert,1995),wherethe</sup> 

7 of 12 

FERRARO AND GIORDANI 

volume, the shape, and the orientation are controlled, respectively, by means of the scalar λg, the diagonal matrix Ag, and the orthogonal matrix Dg. 

A class of models with different geometrical properties is proposed in the literature. For some covariance parametrizations, a closed formula for the M-step in the EM algorithm can be obtained (Celeux & Govaert, 1995). The number of clusters and the parametrization of the covariance matrices are selected using selection criteria, such as the Bayesian information criterion (Schwarz, 1978; Fraley & Raftery, 1998). Obviously, the above model can be extended by using different parametric distributions. Finite mixtures of Gaussian densities are sensitive to outliers. In order to obtain a robust model, a mixture of t distributions can be adopted (Peel & McLachlan, 2000). It represents a heavy-tailed alternative to the component-specific density. As in the Gaussian case, the EM algorithm and the same eigen-decomposition of the covariance matrices are used. In addition, the degrees of freedom are constrained to be equal or not across groups (Andrews & McNicholas, 2012). This produces a class of finite mixture models with t-distributed components called tEIGEN (Andrews & McNicholas, 2012; Andrews, Wickins, Boers, & McNicholas, 2018). As for the fuzzy approach, the use of the noise cluster/component is adopted in, for example, Banfield and Raftery (1993). An alternative approach to handle outliers is based on trimming. Differently from the previously mentioned approaches where the aim is to fit outliers, in the trimming one, outliers are discarded (García-Escudero, Gordaliza, Matrán, & Mayo-Iscar, 2008). The use of trimming in the model-based framework can be found in, for example, Cuesta-Albertos, Matrán, and Mayo-Iscar (2008). 

To face with nonelliptical components, Browne and McNicholas (2015) introduce a mixture of generalized hyperbolic distributions. A further proposal is addressed in Wei, Tang, and McNicholas (2019). It consists of mixtures of generalized hyperbolic distributions and mixtures of skew-t distributions for model-based clustering with incomplete data. 

In case of high-dimensional data, the Gaussian mixture model is highly parametrized. Thus, the dimensionality reduction can improve the performance of the model. The result is a mixture of factor analyzers (McLachlan & Peel, 2000b) that can be fitted by the alternating expectation conditional maximization algorithm (Meng & van Dyk, 1997). A hybridization of the fuzzy and the model-based approaches involving a mixture of factor analyzers is proposed in García-Escudero, Greselin, and Mayo Iscar (2018). This proposal considers a finite mixture of Gaussian densities where Σg in (10) is reparametrized by means of Factor Analysis (see Bartholomew, Knott, & Moustaki, 2011). The membership degrees replace the posterior probabilities and are involved in the robust estimates of the mixture parameters. The EM algorithm is used for estimation. The estimated membership degrees are not conceptually the usual ones of the fuzzy clustering approach but have a probabilistic meaning. 

## 6 | EMPIRICAL COMPARISON 

In this section, in order to compare the performance of the four approaches, a simple two-dimensional dataset is analyzed. All the methods are implemented in R packages. In particular, function FKM of the R package fclust (Ferraro & Giordani, 2015) has been used for the FkM, function pcm of the R package ppclust (Cebeci, Yildiz, Kavlak, Cebeci, & Onder, 2019) for the PkM, function RoughKMeansLW of the R package softclustering (Peters, 2015b) for the RkM and function Mclust of the package mclust (Scrucca, Fop, Murphy, & Raftery, 2016) for FMG. The dataset contains 200 objects, characterized by two clusters. It is included in the R package SoftClustering (see Figure 1). 



<!-- Start of picture text -->
DemoDataC2D2a<br>2 4 6 8 10<br>Feature1<br>12<br>10<br>8<br>6<br>Feature2<br>4<br>2<br><!-- End of picture text -->

FIGURE 1 Scatter plot of the “DemoData2C2Da” dataset 

8 of 12 

FERRARO AND GIORDANI 

|FkM|Feature 1|Feature 2|TABLE 1 Prototypes obtained by the<br>f thd|
|---|---|---|---|
|Clus 1|4.072|3.213|our meos|
|Clus 2|6.874|8.369||
|PkM|Feature 1|Feature 2||
|Clus 1|4.230|3.430||
|Clus 2|6.739|7.905||
|RkM|Feature 1|Feature 2||
|Clus 1|4.975|3.911||
|Clus 2|6.967|7.610||
|FMG|Feature 1|Feature 2||
|Clus 1|4.058|3.217||
|Clus 2|6.909|8.234||



The prototypes resulting from the four algorithms are reported in Table 1. As we can note, those obtained by means of FkM and FMG are very similar, while those obtained by means of RkM are the most different from the others. This is due to the way they are constructed, reported in (6)–(8). The obtained partitions are reported in Figure 2. 

We compare the assignment of some objects that have intermediate characteristics between the two clusters (those colored in yellow between the blue and the green points). The membership degrees, the typicality values, the UAs and the posterior probabilities for FkM, PkM, RkM, and FMG, respectively, are reported in Table 2. 

As we can see, for most of these objects, except for 83, 97, 163, the UAs to both the clusters are equal to 1. The membership degrees are lower than 0.7, while the degrees of typicality are lower than 0.43 for both the clusters. In case of FMG, the 



<!-- Start of picture text -->
Fuzzy k−means Possibilistic k−means<br>2 4 6 8 10 2 4 6 8 10<br>Feature1 Feature1<br>Rough k−means Finite mixture model<br>2 4 6 8 10 2 4 6 8 10<br>Feature1 Feature1<br>12 12<br>10 10<br>8 8<br>6 6<br>Feature2 Feature2<br>4 4<br>2 2<br>12 12<br>10 10<br>8 8<br>6 6<br>Feature2 Feature2<br>4 4<br>2 2<br><!-- End of picture text -->

FIGURE 2 Partitions obtained by the four methods. Blue points indicate Cluster 1, green points indicate Cluster 2 and yellow points denote objects with membership degrees lower than 0.7 for FkM, objects with typicality values lower than 0.5 for PkM, objects in both the upper approximations for RkM and objects with posterior probabilities lower than 0.7 for FMG 

9 of 12 

FERRARO AND GIORDANI 

|TABLE 2 Membership degrees,<br>typicality values, upper approximations,||FkM||PkM||RkM||FMG||
|---|---|---|---|---|---|---|---|---|---|
|and posterior probabilities for some|Obj|Clus 1|Clus 2|Clus 1|Clus 2|Clus 1|Clus 2|Clus 1|Clus 2|
|uncertain assignments|83|0.392|0.608|0.291|0.340|0|1|0.419|0.581|
||97|0.369|0.631|0.239|0.304|0|1|0.404|0.581|
||120|0.578|0.422|0.336|0.216|1|1|0.891|0.109|
||124|0.680|0.320|0.300|0.135|1|1|0.984|0.016|
||136|0.692|0.308|0.236|0.102|1|1|0.993|0.007|
||143|0.651|0.349|0.361|0.181|1|1|0.959|0.041|
||163|0.324|0.676|0.207|0.311|0|1|0.264|0.736|
||181|0.687|0.313|0.347|0.153|1|1|0.981|0.019|
||185|0.574|0.426|0.389|0.255|1|1|0.828|0.172|
||187|0.634|0.366|0.424|0.232|1|1|0.892|0.108|
||190|0.440|0.560|0.208|0.211|1|1|0.598|0.402|



posterior probabilities are higher than the membership and typicality degrees. On the contrary, objects 83 and 97 and 163 are completely assigned to cluster 2 by RkM, while they are assigned to cluster 2 by FkM and FMG, respectively, with membership degrees between 0.61 and 0.68, and posterior probabilities between 0.58 and 0.74. 

## 7 | CONCLUSIONS 

Most of soft clustering methods are summarized in this review. In particular, we focused on four soft approaches for clustering: fuzzy, possibilistic, rough, and model-based. Although we showed that they are quite similar from a practical point of view, the theory behind is different, mainly for some of them. We briefly recalled the main features of the most known methods for each approach: the FkM, the possibilistic k means, the RkM, and the FMG distributions. The assignments of the objects to the clusters are made by means of the membership degrees, the degrees of typicality, and the UAs, respectively, in the fuzzy, possibilistic, and rough frameworks. A separate discussion deserves the model-based approach, that we consider as a soft approach to clustering but it is the most different one from a theoretical point of view, since probabilistic assumptions are made. In this case, the assignments are provided by the posterior probabilities that play a role similar to the one of the membership degrees. 

It will be interesting to carry out simulation studies in order to compare the behavior of the various soft clustering approaches. Different scenarios should be taken into consideration. 

### CONFLICT OF INTEREST 

The authors have declared no conflicts of interest for this article. 

### RELATED WIREs ARTICLES 

<u>Model-based cluster analysis Fuzzy set theory Rough clustering</u> 

### ORCID 

Maria Brigida Ferraro https://orcid.org/0000-0002-7686-5938 

### REFERENCES 

Andrews, J. L., & McNicholas, P. D. (2012). Model-based clustering, classification, and discriminant analysis via mixtures of multivariate t-distributions. Statistics and Computing, 22, 1021–1029. https://doi.org/10.1007/s11222-011-9272-x 

10 of 12 

FERRARO AND GIORDANI 

- Andrews, J. L., Wickins, J. R., Boers, N. M., & McNicholas, P. D. (2018). teigen: An R package for model-based clustering and classification via the multivariate t distribution. Journal of Statistical Software, 83(7), 1–32. https://doi.org/10.18637/jss.v083.i07 

- Antoine, V., Quost, B., Masson, M.-H., & Denoeux, T. (2012). CECM: Constrained evidential c-means algorithm. Computational Statistics and Data Analysis, 56(4), 894–914. https://doi.org/10.1016/j.csda.2010.09.021 

Banfield, J. D., & Raftery, A. E. (1993). Model-based gaussian and non-gaussian clustering. Biometrics, 49, 803–821. 

- Barni, M., Cappellini, V., & Mecocci, A. (1996). Comments on ‘a possibilistic approach to clustering’. IEEE Transactions on Fuzzy Systems, 4, 393–396. https://doi.org/10.1109/91.531780 

Bartholomew, D. J., Knott, M., & Moustaki, I. (2011). Latent variable models and factor analysis: A unified approach. Chichester, England: John Wiley & Sons, Inc. 

Bezdek, J. C. (1981). Pattern recognition with fuzzy objective function algorithm. New York, NY: Plenum Press. 

- Browne, R. P., & McNicholas, P. D. (2015). A mixture of generalized hyperbolic distributions. Canadian Journal of Statistics, 43(2), 176–198. https://doi.org/10.1002/cjs.11246 

- Cebeci, Z., Yildiz, F., Kavlak, A. T., Cebeci, C., & Onder, H. (2019). ppclust: Probabilistic and possibilistic cluster analysis [Computer software 

manual]. Retrieved from https://CRAN.R-project.org/package=ppclust (R package version 0.1.2) 

- Celeux, G., & Govaert, G. (1995). Gaussian parsimonious clustering models. Pattern Recognition, 28, 781–793. https://doi.org/10.1016/0031-3203 (94)00125-6 

Chen, M., & Miao, D. (2011). Interval set clustering. Expert Systems with Applications, 38, 2923–2932. https://doi.org/10.1016/j.eswa.2010.06.052 

Cuesta-Albertos, J. A., Matrán, C., & Mayo-Iscar, A. (2008). Robust estimation in the normal mixture model based on robust clustering. Journal of Royal Statistical Society Series B, 70, 779–802. https://doi.org/10.1111/j.1467-9868.2008.00657.x 

- Davé, R. N. (1991). Characterization and detection of noise in clustering. Pattern Recognition Letters, 12(11), 657–664. https://doi.org/10.1016/ 0167-8655(91)90002-4 

- Davé, R. N., & Sen, S. (2002). Robust fuzzy clustering of relational data. IEEE Transactions on Fuzzy Systems, 10(6), 713–727. https://doi.org/10. 1109/TFUZZ.2002.805899 

Dempster, A. P., Laird, N. M., & Rubin, D. B. (1977). Maximum likelihood from incomplete data via the EM algorithm. Journal of Royal Statistical Society Series B, 39, 1–38. 

de Oliveira, J. V., & Pedrycz, W. (2007). Advances in fuzzy clustering and its applications. Chichester, England: John Wiley & Sons. 

- Ferone, A., & Maratea, A. (2019). Integrating rough set principles in the graded possibilistic clustering. Information Sciences, 477, 148–160. https:// doi.org/10.1016/j.ins.2018.10.038 

- Ferraro, M. B., & Giordani, P. (2013). A new fuzzy clustering algorithm with entropy regularization. In T. Minerva, I. Morlini, & F. Palumbo (Eds.), Book of abstracts of cladag 2013—9th meeting of the classification and data analysis group, pp. 195–198. Italy: Cleup. 

- Ferraro, M. B., & Giordani, P. (2015). A toolbox for fuzzy clustering using the R programming language. Fuzzy Sets and Systems, 279, 1–16. https://doi.org/10.1016/j.fss.2015.05.001 

- Fraley, C., & Raftery, A. E. (1998). How many clusters? Which clustering method? Answers via model-based cluster analysis. The Computer Journal, 41, 578–588. https://doi.org/10.1093/comjnl/41.8.578 

- Fraley, C., & Raftery, A. E. (2002). Model-based clustering, discriminant analysis, and density estimation. Journal of American Statistical Association, 97, 611–631. https://doi.org/10.1198/016214502760047131 

- García-Escudero, L. A., Gordaliza, A., Matrán, C., & Mayo-Iscar, A. (2008). A general trimming approach to robust cluster analysis. The Annals of Statistics, 36, 1324–1345. https://doi.org/10.1214/07-AOS515 

- García-Escudero, L. A., Greselin, F., & Mayo Iscar, A. (2018). Robust, fuzzy, and parsimonious clustering, based on mixtures of factor analyzers. International Journal of Approximate Reasoning, 94, 60–75. https://doi.org/10.1016/j.ijar.2018.01.001 

- Gustafson, D. E., & Kessel, W. C. (1978). Fuzzy clustering with a fuzzy covariance matrix. In Proceedings of IEEE conference on decision and control including the 17th symposium on adaptive processes (pp. 761–766). San Diego, CA: IEEE. 

- Hathaway, R. J. J., Devenport, J. W. W., & Bezdek, J. C. (1988). Relation duals of the c-means clustering algorithms. Pattern Recognition, 22, 205–212. https://doi.org/10.1016/0031-3203(89)90066-6 

- Hennig, C., Meila, M., Murtagh, F., & Rocci, R. (2015). Handbook of cluster analysis. Boca Raton, FL: Chapman and Hall CRC. 

- Kaufman, L., & Rousseuw, P. J. (1990). Finding groups in data: An introduction to cluster analysis. New York, NY: Wiley. 

- Klawonn, F., & Höppner, F. (2003). An alternative approach to the fuzzifier in fuzzy clustering to obtain better clustering. In Proceedings of eusflat conference (pp. 730–734). Zittau, Germany. 

- Klawonn, F., Kruse, R., & Winkler, R. (2015). Fuzzy clustering: More than just fuzzification. Fuzzy Sets and Systems, 281, 272–279. https://doi.org/ 10.1016/j.fss.2015.06.024 

- Krishnapuram, R., Joshi, A., Nasraoui, O., & Yi, L. (2001). Low-complexity fuzzy relational clustering algorithms for web mining. IEEE Transactions on Fuzzy Systems, 9, 595–607. https://doi.org/10.1109/91.940971 

- Krishnapuram, R., & Keller, J. M. (1993). A possibilistic approach to clustering. IEEE Transactions on Fuzzy Systems, 1(2), 98–110. https://doi.org/ 10.1109/91.227387 

- Krishnapuram, R., & Keller, J. M. (1996). The possibilistic c-means algorithm: Insights and recommendations. IEEE Transactions on Fuzzy Systems, 4, 385–393. https://doi.org/10.1109/91.531779 

- Li, F., Ye, M., & Chen, X. (2014). An extension to rough c-means clustering based on decision-theoretic rough sets model. International Journal of Approximate Reasoning, 55, 116–129. https://doi.org/10.1016/j.ijar.2013.05.005 

11 of 12 

FERRARO AND GIORDANI 

- Li, R. P., & Mukaidono, M. (1995). A maximum-entropy approach to fuzzy clustering. In Proceedings of fuzzy systems, 1995—International joint conference of the fourth ieee international conference on fuzzy systems and the second international fuzzy engineering symposium (pp. 2227–2232). Yokohama, Japan. 

- Li, R. P., & Mukaidono, M. (1999). Gaussian clustering method based on maximum-fuzzy-entropy interpretation. Fuzzy Sets and Systems, 102, 253–258. https://doi.org/10.1016/S0165-0114(97)00126-7 

- Lingras, P. (2007). Applications of rough set based k-means, Kohonen SOM, GA clustering. In J. F. Peters, A. Skowron, V. W. Marek, E. Orłowska, R. Słowi�nski, & W. Ziarko (Eds.), Transactions on rough sets VII (Vol. 4400, pp. 120–139). Berlin, Heidelberg: Springer-Verlag. https://doi.org/10.1007/978-3-540-71663-1_8 

- Lingras, P., & West, C. (2004). Interval set clustering of web users with rough k-means. Journal of Intelligent Information Systems, 23, 5–16. https://doi.org/10.1023/B:JIIS.0000029668.88665.1a 

- MacQueen, J. B. (1967). Some methods for classi cation and analysis of multivariate observations. In Proceedings of the fifth Berkeley symposium on mathematical statistics and probability (Vol. 560, pp. 281–297). Berkeley: University of California Press. 

- Maji, P., & Pal, S. K. (2007). Rfcm: A hybrid clustering algorithm using rough and fuzzy sets. Fundamenta Informaticae, 80, 475–496. 

- Masson, M.-H., & Denoeux, T. (2008). Ecm: An evidential version of the fuzzy c-means algorithm. Pattern Recognition, 41(4), 1384–1397. https:// doi.org/10.1016/j.patcog.2007.08.014 

- Masson, M.-H., & Denoeux, T. (2009). RECM: Relational evidential c-means algorithm. Pattern Recognition Letters, 30(4), 1015–1026. https://doi. org/10.1016/j.patrec.2009.04.008 

- McLachlan, G., & Krishnan, T. (2008). The EM algorithm and extensions. New York, NY: Wiley. 

McLachlan, G., & Peel, D. (2000a). Finite mixture models. Hoboken, NJ: John Wiley & Sons, Inc. 

- McLachlan, G., & Peel, D. (2000b). Mixtures of factor analyzers. In Proceedings of the seventeenth international conference on machine learning (pp. 599–606). San Francisco: Morgan Kaufmann. 

- Ménard, M., Courboulay, V., & Pierre-André, D. (2003). Possibilistic and probabilistic fuzzy clustering: Unification within the framework of the non-extensive thermostatistics. Pattern Recognition, 36, 1325–1342. https://doi.org/10.1016/S0031-3203(02)00049-3 

- Meng, X.-L., & van Dyk, D. (1997). The EM algorithm—An old folk song sung to a fast new tune (with discussion). Journal of Royal Statistical Society Series B, 59, 511–567. https://doi.org/10.1111/1467-9868.00082 

- Mitra, S. (2004). An evolutionary rough partitive clustering. Pattern Recognition Letters, 25, 1439–1449. https://doi.org/10.1016/j.patrec.2004. 05.007 

- Mitra, S., Banka, H., & Pedrycz, W. (2006). Rough-fuzzy collaborative clustering. IEEE Transactions on Systems, Man, and Cybernetics - Part B: Cybernetics, 36(4), 795–805. 

- Mitra, S., Pedrycz, W., & Barman, B. (2010). Shadowed c-means: Integrating fuzzy and rough clustering. Pattern Recognition, 43, 1282–1291. https://doi.org/10.1016/j.patcog.2009.09.029 

- Pal, N. R., Pal, K., & Bezdek, J. C. (1997). A mixed c-means clustering model. In Proceedings of fuzz-IEEE’97 (pp. 11–21). Barcelona, Spain. 

- Pal, N. R., Pal, K., Keller, J. M., & Bezdek, J. C. (2005). A possibilistic fuzzy c-means clustering algorithm. IEEE Transactions on Fuzzy Systems, 13, 517–530. https://doi.org/10.1109/TFUZZ.2004.840099 

- Pawlak, Z. (1982). Rough sets. International Journal of Information and Computer Sciences, 11, 145–172. https://doi.org/10.1007/BF01001956 

Pawlak, Z. (1992). Rough sets: Theoretical aspects of reasoning about data. MA: Kluwer Academic Publishers Norwell. 

Peel, D., & McLachlan, G. (2000). Robust mixture modelling using the t distribution. Statistics and Computing, 10, 339–348. https://doi.org/10. 1023/A:1008981510081 

Peters, G. (2005). Outliers in rough k-means clustering. In Springer-Verlag (Ed.), Proceedings of PreMI 2005—1st international conference on pattern recognition and machine intelligence (Vol. 3776, pp. 702–707). Berlin, Heidelberg, Germany: Springer. 

Peters, G. (2006). Some refinements of rough k-means. Pattern Recognition, 39, 1481–1491. https://doi.org/10.1016/j.patcog.2006.02.002 

Peters, G. (2014). Rough clustering utilizing the principle of indifference. Information Sciences, 277, 358–374. https://doi.org/10.1016/j.ins.2014. 02.073 

Peters, G. (2015a). Is there any need for rough clustering? Pattern Recognition Letters, 53, 31–37. https://doi.org/10.1016/j.patrec.2014.11.003 

Peters, G. (2015b). SoftClustering: Soft clustering algorithms [Computer software manual]. Retrieved from https://CRAN.R-project.org/package= SoftClustering (R package version 1.1502) 

Peters, G., Crespo, F., Lingras, P., & Weber, R. (2013). Soft clustering - fuzzy and rough approaches and their extensions and derivatives. International Journal of Approximate Reasoning, 54, 307–322. https://doi.org/10.1016/j.ijar.2012.10.003 

Peters, G., & Lampart, M. (2006). A partitive rough clustering algorithm. In Proceedings of rsctc 2006—5th international conference on rough sets and current trends in computing (Vol. 4259, pp. 657–666). Berlin, Germany: Springer-Verlag. 

Peters, G., Lampart, M., & Weber, R. (2008). Evolutionary rough k-medoid clustering. In J. F. Peters & A. Skowron (Eds.), Transactions on rough 

sets VIII (Vol. 5084, pp. 289–306). Berlin, Heidelberg: Springer-Verlag. 

Peters, G., & Lingras, P. (2011). Rough clustering. WIREs Data Mining and Knowledge Discovery, 1, 64–72. https://doi.org/10.1002/widm.16 

Peters, G., Weber, R., & Nowatzke, R. (2012). Dynamic rough clustering and its applications. Applied Soft Computing, 12, 3193–3207. https://doi. org/10.1016/j.asoc.2012.05.015 

Schwarz, G. (1978). Estimating the dimension of a model. The Annals of Statistics, 6(2), 461–464. 

- Scrucca, L., Fop, M., Murphy, T. B., & Raftery, A. E. (2016). mclust 5: Clustering, classification and density estimation using Gaussian finite mixture models. The R Journal, 8, 289–317. 

12 of 12 

FERRARO AND GIORDANI 

- Timm, H., Borgelt, C., Doring, C., & Kruse, R. (2004). An extension to possibilistic fuzzy cluster analysis. Fuzzy Sets and Systems, 147, 3–16. https://doi.org/10.1016/j.fss.2003.11.009 

- Wei, Y., Tang, Y., & McNicholas, P. D. (2019). Mixtures of generalized hyperbolic distributions and mixtures of skew-t distributions for modelbased clustering with incomplete data. Computational Statistics and Data Analysis, 130, 18–41. https://doi.org/10.1016/j.csda.2018.08.016 

- Yang, M.-S., & Wu, K.-L. (2006). Unsupervised possibilistic clustering. Pattern Recognition, 39, 5–21. https://doi.org/10.1016/j.patcog.2005. 07.005 

- Yiming, T., Xianghui, H., & Pedrycz, W. (2019). Possibilistic fuzzy clustering with high-density viewpoint. Neurocomputing, 329, 176–198. https:// doi.org/10.1016/j.neucom.2018.11.007 

How to cite this article: Ferraro MB, Giordani P. Soft clustering. WIREs Comput Stat. 2019;e1480. <u>https://doi.org/10. 1002/wics.1480</u> 

