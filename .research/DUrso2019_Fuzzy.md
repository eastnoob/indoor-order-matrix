1 

# Fuzzy clustering with spatial-temporal information 

2 

Pierpaolo D’Urso<sup>1,</sup><sup>_∗_</sup> , Livia De Giovanni<sup>b</sup> , Marta Disegna<sup>c</sup> , Riccardo Massari<sup>1</sup> 

3 _aDepartment of Social Sciences and Economics, Sapienza University of Roma, P.le Aldo Moro 5, 00185_ 4 _Roma, Italy_ 5 _bDepartment of Political Sciences, LUISS Guido Carli, Rome, Italy_ 

6 _cAccounting, Finance & Economics Department, Faculty of Management, Bournemouth University, 89_ 7 _Holdenhurst Road, Bournemouth, BH8 8EB, United Kingdom_ 

7 

## 8 **Abstract** 

Clustering geographical units based on a set of quantitative features observed at several time occasions requires to deal with the complexity of both space and time information. In particular, one should consider (1) the spatial nature of the units to be clustered, (2) the characteristics of the space of multivariate time trajectories, and (3) the uncertainty related to the assignment of a geographical unit to a given cluster on the basis of the above complex features. This paper discusses a novel spatially constrained multivariate time series clustering for units characterised by different levels of spatial proximity. In particular, the Fuzzy Partitioning Around Medoids algorithm with Dynamic Time Warping dissimilarity measure and spatial penalization terms is applied to classify multivariate Spatial-Temporal series. The clustering method has been theoretically presented and discussed using both simulated and real data, highlighting its main features. In particular, the capability of embedding different levels of proximity among units, and the ability of considering time series with different length. 

9 _Keywords:_ Fuzzy Clustering, Partitioning Around Medoids, Time Series, Spatial 10 information, Dynamic Time Warping, Tourism, Multilevel spatial proximity 

11 

## **1. Introduction** 

12 As Caiado et al. (2015) highlights, the (1) model- (2) feature- and (3) observation13 based approaches are the main methodological veins developed in the past to aggregate 14 units characterised by similar behaviour across time (for more details, see also Warren Liao, 15 2005; Caiado et al., 2015; D’Urso et al., 2016). 

16 The idea behind the model-based clustering algorithms is to find the best mathemat17 ical/statistical model able to describe given time-varying data. The clustering is then 18 performed on the parameter estimates (or on the residuals) of the fitted models (see, e.g., 19 Piccolo, 1990; Maharaj, 1996; Garcia-Escudero & Gordaliza, 1999; Kalpakis et al., 2001; 20 James & Sugar, 2003; Alonso & Maharaj, 2006; Caiado & Crato, 2010; Otranto, 2010; 21 D’Urso et al., 2013b,a, 2016; D’Urso et al., 2017). Examples of model-based fuzzy cluster- 

- 22 ing algorithms for univariate time series can be found in D’Urso et al. (2013a,b). 

> _∗_ Corresponding author _PreprintEmailsubmittedaddresses:to_ `pierpaolo.durso@uniroma1.it` _Spatial Statistics_ (Pierpaolo D’Urso), `ldegiovanni@luiss.it` _March 28, 2019_ (Livia De Giovanni), `disegnam@bournemouth.ac.uk` (Marta Disegna), `Riccardo.massari@uniroma1.it` (Riccardo Massari) 

- 23 Following the feature-based clustering approach, time series are clustered according to 24 one of their specific features, such as the autocorrelation function (ACF), the periodogram, 

- 25 the density function or the wavelet information (see, e.g., Alonso & Maharaj, 2006; Caiado 26 et al., 2006, 2009; D’Urso & Maharaj, 2009; Maharaj & D’Urso, 2010, 2011; D’Urso & 

- 27 Maharaj, 2012; D’Urso et al., 2014; Lafuente-Rego & Vilar, 2016; Vilar et al., 2017). In 28 the fuzzy clustering framework, both univariate and multivariate time series wavelet fea29 tures have been considered in Maharaj et al. (2010) and D’Urso & Maharaj (2012), while 30 frequency domains of univariate time series have been taken into account in Maharaj & 31 D’Urso (2011). 

- 32 Observed time series, or suitable transformations, are instead the segmentation data 33 used in the observation-based approach (see, e.g., D’Urso, 2005a; Coppi et al., 2010, and 34 references therein). In the last decade, different fuzzy clustering algorithms have been 35 proposed for both univariate and multivariate time series (see, e.g., Coppi & D’Urso, 2002, 36 2003, 2006; D’Urso, 2005b; D’Urso et al., 2015, 2016; D’Urso et al., 2017; D’Urso et al., 37 2017; Vilar et al., 2017). 

- 38 Similarly, different methods have been suggested in the clustering literature to discover 39 spatial patterns for different kind of spatial units, e.g., urban areas or image pixels. The 40 main challenge these methods deal with is the identification of an appropriate algorithm 41 to capture both spatial dependence and spatial heterogeneity. Following the categorisation 42 suggested by Caiado et al. (2015), Fouedjio (2016) classifies clustering of spatial data 

- 43 into four main approaches: (1) non-spatial clustering with geographical coordinates as 44 additional variables; (2) non-spatial clustering based on a spatial dissimilarity measure; 

- 45 (3) spatially constrained clustering; (4) model-based clustering. An example of spatially 46 constrained fuzzy algorithm for urban areas is provided by Di Nola et al. (2000). Examples 47 of applications for image pixels segmentation can be found in Tolias & Panas (1998a,b); 48 Pham & Prince (1999); Liew et al. (2000, 2003); Pham (2001); Liew et al. (2003); Chuang 49 et al. (2006). 

- 50 A fifth approach worth of notice consists in including a spatial penalty term in the 51 objective function of the clustering method, as suggested by Pham (2001). While this 52 proposal has been introduced for solving image segmentation problem, the idea beyond 53 can be easily extended to the clustering of geographical areas (Coppi et al., 2010). 

- 54 When time information are available for space unit, the spatial time data array is a 55 three-way data array (i.e. arrays of the type: spatial objects _×_ variables _×_ occasions). 56 The spatial time data array **X** can be reduced to a _bi_ -dimensional array by combining two 57 of the three dimensions on the rows and assigning the remaining dimension to the columns 58 (Krishnapuram & Freg, 1992; Shekhar et al., 2015). This dimensionality reduction allows 

- 59 for the classification of units by means of a traditional clustering technique at the expense 

- 60 of information loss. To overcome this drawback, several clustering for spatial-temporal 

- 61 series have been suggested in the literature. Following Disegna et al. (2017), clustering of 

- 62 spatial-temporal series can be classified into: (i) non-spatial time series clustering based on 

- 63 a spatial dissimilarity measure (Izakian et al., 2013); (ii) density-based clustering (Ester 

- 64 et al., 1996; Wang et al., 2006; Birant & Kut, 2007; Ienco & Bordogna, 2016; Xie et al., 65 2016); (iii) model-based clustering (Basford & McLachlan, 1985; Viroli, 2011; Torabi, 2014, 

2 

- 66 2016; Disegna et al., 2017); (iv) spatially constrained time series clustering (Hu & Sung, 

- 67 2006; Coppi et al., 2010; Gao & Yu, 2016). Three-way data arrays have also been analysed 

- 68 by means of several fuzzy clustering algorithms (see, e.g., Sato & Sato, 1994; Sato et al., 

- 69 1997; Gordon & Vichi, 2001; D’Urso, 2004, 2005a; Coppi et al., 2010). As for space data, 

- 70 Coppi et al. (2010) proposed the inclusion of the spatial penalty term in the objective 71 function of a fuzzy clustering algorithm for spatial-temporal data too. The aim of this 72 term is to reduce the membership degrees of all units contiguous to the generic _i_ -th unit 73 computed in all clusters but the _c_ -th cluster to which the _i_ -th unit belongs (Coppi et al., 74 2010). 

- 75 In this study a generalisation of the fuzzy clustering algorithm with spatial penalization 76 introduced by Coppi et al. (2010) is proposed. In particular, the innovation is threefold: 77 firstly, we suggest to substitute the Euclidean distance with the Dynamic Time Warping 78 (DTW) dissimilarity measure; secondly, we extend the Coppi et al. (2010)’s algorithm to 79 the case in which data are characterised by different sources of spatial information; thirdly, 80 a measure of spatial autocorrelation, the Fuzzy Moran ( _FM_ )’s index, is defined to study 81 the autocorrelation of the final imprecise partition when several spatial penalty terms are 82 considered. 

- 83 The DTW dissimilarity measure has been selected instead of other more traditional 84 distance measures, such as the well known Euclidean distance, mainly for its flexibility, the 85 possibility to simultaneously consider both intensity and dynamic existing between time 86 series, and thanks to its ability to compute distance among multivariate time series not 87 necessarily of the same length. 

- 88 The necessity to consider more than one spatial penalty term in the clustering algorithm 89 is motivated by practical case studies in which units are characterised by different levels, 90 or concepts, of proximity. For instance, European region are classified into three levels of 91 Nomenclature of Territorial Units for Statistics (NUTS) geography classification and any 92 clustering analysis of European cities should take into consideration these three levels. 

- 93 Therefore, the Dynamic Time Warping Fuzzy _C_ -Medoids for Spatial-Temporal Trajec94 tories (DTW-FCMd-STT) clustering algorithm with penalty terms is proposed and de95 scribed in this manuscript. 

- 96 The paper is structured as follows: in section 2 the suggested algorithm is described 97 and discussed in depth; in section 3 different simulated case studies are presented in order 98 to show the main features of the algorithm; in section 4 the methodology is illustrated 99 by analysing real data describing the behaviour of the tourism flows in a destination, i.e. 

- 100 spatial region. section 5 concludes. 

101 

## **2. The methodology** 

102 The starting point is represented by a spatial time data array (three-way data array), 103 algebraically formalised as (D’Urso, 2000, 2004, 2005a): 



3 

104 where _i_ indicates the generic unit (geographical area or region), _j_ the variable, and _t_ the 105 generic time; _xijtijt_ is the value of the _j_ -th variable observed for the _i_ -th unit at time _t_ . 

105 generic time; _xijtijt_ is the value of the _j_ -th variable observed for the _i_ -th unit at time _t_ . Notice that the time data array **X** can be synthetically represented by means of a _bi_ - dimensional matrix combining two of the three indices _i, j, t_ on the rows and assigning the remaining index to the columns. For instance, the time data array can be defined as the set of _bi_ -dimensional matrices **X** _i,_ **X** _t_ , or **X** _j_ as follows: 



106 We also assume to have _K_ additional pieces of information on spatial location of each 107 units in relation with the others, i.e., _K_ different levels of spatial proximity. Each level of 108 proximity is defined by a ( _I × I_ ) symmetric data matrix **P** _k_ ( _k_ = 1 _, . . . , K_ ), whose generic 109 entry _pkii′_ is a measure of a particular definition of spatial proximity between the _i_ -th and 110 _i_<sup>_′_</sup> -th units ( _i, i_<sup>_′_</sup> = 1 _, . . . , I_ ), where 0 _≤ pkii′ ≤_ 1 and _pkii_ = 0. For instance, _pkii′_ = 1 if 111 the two areas are contiguous, _pkii′_ = 0 otherwise. Alternatively, _pkii′_ could be inversely 112 proportional to the geographic distance between _i_ and _i_<sup>_′_</sup> . We will further illustrate different 113 kind of proximity matrix in section 2.2. 

114 Figure 1 graphically represents the bundle of available information and the dimensions 115 of the data array typically used in spatial-temporal analysis. 



<!-- Start of picture text -->
Spatial static information  Space-time data array<br>on geographical units<br>I P 1<br>I<br>I P 2<br>I T<br>I<br>⋮ J<br>I Legend:<br>I  geographical units<br>J  time-varying observed variables<br>P K T  period of time<br>I<br><!-- End of picture text -->

Figure 1: Spatial-temporal data array 

116 For classification purpose, the _i_ -th multivariate time trajectory is formalized by the 

4 

117 matrix **X** _i ≡{_ **x** _it_ : _t_ = 1 _, . . . , T }_ , where **x** _it ≡_ ( _xi_ 1 _t, . . . , xijt, . . . , xiJt_ ) _, i_ = 1 _, . . . , I, t_ = 118 1 _, . . . , T_ . 

119 _2.1. Dynamic Time Warping_ 

120 The Dynamic Time Warping (DTW) (Velichko et al., 1970; Berndt, 1994; Izakian et al., 121 2015; D’Urso et al., 2018) allows to locally stretch or compress multivariate time series to 122 make their shape as similar as possible. 

- 123 To this end, the functions that allow to remap each multivariate time series need to be 124 identified. This kind of function is called warping function and its aim is to “realign” the 125 time indices of the multivariate time series. 

125 

126 Given a “query” (or test) multivariate time series **X** _i_ and a “reference” multivariate 127 time series, **X** _i′_ , with length _T_ and _T_<sup>_′_</sup> ( _T_ ⋛ _T_<sup>_′_</sup> ) respectively, the total distance between **X** _i_ 128 and **X** _i′_ is computed by means of the warping path. The warping path allows to compare 129 each data point in **X** _i_ with the closest data point in **X** _i′_ , and is defined as 



under the following constraints. 

130 

1. boundary condition: Φ11 = (1 _,_ 1) _,_ Φ _L_ = ( _T, T_<sup>_′_</sup> ); 

131 1. boundary condition: Φ11 = (1 _,_ 1) _,_ Φ _L_ = ( _T, T_<sup>_′_</sup> ); 132 2. monotonicity condition: _ϕ_ 1 _≤ . . . ≤ ϕl ≤ . . . ≤ ϕL_ and _ψ_ 1 _≤ . . . ≤ ψl ≤ . . . ≤ ψL_ . 

133 The total dissimilarity between the two “warped” multivariate time series is: 



- 134 where _ml,_ Φ is a local weighting coefficient, and _d_ ( _., ._ ) is, usually, the Euclidean distance 

- 135 for multivariate time series (Giorgino et al., 2009). Since there are several warping curves, 136 the DTW dissimilarity measure is the one which correspond to the optimal warping curve, 137 ˆΦ _l_ = ( ˆ _ϕl, ψ_ ˆ _l_ ) _,_ ( _l_ = 1 _, . . . , L_ ), which minimizes the total dissimilarity between **X** _i_ and **X** _i′_ : 



138 The DTW dissimilarity measure is particularly useful when comparing multivariate 139 time series. First, by preserving the time ordering of the sequence, the DTW goes beyond 140 the instantaneous features of time data. Indeed, DTW dissimilarity measure copes with 141 both the instantaneous and the variational features of the multivariate time trajectories, 142 i.e., the instantaneous position of the trajectories and their dynamic evolution over time, 143 thus providing a more complete comparison that takes into account also the different rates 144 at which phenomena change over times. Second the DTW dissimilarity measure is also 145 more flexible than the Euclidean distance since it allows for comparison of multivariate time 

- 146 series of different lengths. Third, no assumptions are required regarding the multivariate 

5 

- 147 time series properties. Furthermore, Euclidean distance is calculated in a one-to-one man148 ner, while DTW dissimilarity measure tries to find the best warping. Finally, by taking 149 explicitly into account the ordering of the observations, DTW also deals with the presence 150 of possible time shits in the data. 

- 151 For all these reasons, DTW is now usually adopted as a suitable alternative to Euclidean 152 distance in time series cluster analysis (see, among others, Berndt, 1994; Oates et al., 1999; 153 Jeong et al., 2011; Petitjean et al., 2011; Begum et al., 2015; Izakian et al., 2015; Mure et al., 154 2016) In particular, Ding et al. (2008) and Rakthanmanon et al. (2012) experimentally 155 proved the effectiveness of DTW in data mining problems—like time series clustering is— 156 with respect to other distance measures. 

- 157 Furthermore, while DTW is more computationally demanding than Euclidean distance, 158 by adopting a Partitioning-Around-Medoids (PAM, Kaufman & Rousseeuw, 2005) ap159 proach (see section 2.3 below), the distance matrix should be computed only once at the 160 start of the overall clustering procedure (D’Urso et al., 2018). 

- 161 _2.2. Dealing with space: proximity matrix_ 

- 162 When dealing with spatial data the within group dispersion has to be minimised and the 

- 163 spatial autocorrelation between contiguous spatial units has to be taken into consideration. 164 This spatial information can be analytically embedded in the clustering process using a 165 “proximity” matrix, say **P** , that is a symmetric matrix of order _I_ whose elements signal the 166 proximity between two spatial areas (Pham, 2001; Coppi et al., 2010). In the literature, 167 there are different ways of defining proximity and consequently there are different ways of 168 constructing proximity matrices among spatial units (Gordon, 1999; P´aez & Scott, 2005). 169 Two of the most common definitions are based on connectivity, i.e. travel time or distance 170 between pairs of units, and physical contiguity. 

- 171 Connectivity can be coped with by means of a proximity matrix **P** whose elements 172 are given by the inverse of a generic measure of the distance between _i_ and _i_<sup>_′_</sup> (distance 173 between the two spatial units, trip duration and/or cost, etc.), normalized to range in 174 [0 _,_ 1]. The more two spatial areas are connected, the lower is the value in the proximity 175 matrix. Obviously, diagonal elements are all equal to 0. 176 Spatial contiguity, on its turn, can be specified in several ways. For instance, two 177 spatial units can be contiguous either if they are adjacent (neighbours) or if they belong 178 to the same macro-area, even if they are not adjacent. In this case, **P** is constructed as a 179 symmetric matrix with 0 diagonal elements and with off-diagonal elements given by: 



180 _2.3. The DTW-Fuzzy C-Medoids clustering algorithm for Spatial-Temporal Trajectories_ 181 _(DTW-FCMd-STT)_ 

- 182 In this paper, following a PAM apprach in a fuzzy framework, the Fuzzy _C_ -Medoids 183 (FCMd, Krishnapuram et al., 2001) clustering algorithm is adopted. With respect to stan184 dard (crisp) clustering algorithms, fuzzy clustering algorithms are generally more efficient— 185 dramatic changes in the value of cluster membership are less likely to occur in estimation 

6 

- 186 procedures—and they are less affected by both local optima and convergence problems 187 (Everitt et al., 2001; Hwang et al., 2007). With complex data as multivariate time series 188 are, it could be difficult to identify a clear boundary between clusters in real applications. 189 In this sense, fuzzy clustering appears more attractive than the crisp clustering methods 190 **?** Wedel & Kamakura (2000). Finally, the membership degrees produced by fuzzy cluster191 ing methods, that indicate the belonging of each unit to each cluster, also indicate whether 192 there is a second-best cluster almost as good as the best cluster, a scenario which crisp 193 clustering methods cannot uncover Everitt et al. (2001). 

- 194 Regarding the choice of the fuzzy clustering method, with respect to Fuzzy _C_ -Means 195 (FCM, Bezdek, 1981), FCMd allows for more appealing and easy to interpret results of the 196 final partition (Kaufman & Rousseeuw, 2005) by obtaining non-fictitious representative 197 time series (i.e. the medoids) as final result (see section 2.6). 198 Dealing with Spatial-Temporal trajectories, possible spillover effects between adjacent 199 units have to be taken into account. As observed in section 2.2, since there could be 200 different, say _K_ ( _K ≥_ 1), definitions of proximity, _K_ spatial penalty terms are added to 201 the objective function. Following Pham & Prince (1999) and Coppi et al. (2010), the 202 DTW-Fuzzy _C_ -Medoids clustering algorithm for Spatial-Temporal Trajectories (DTW203 FCMd-STT) is then formalised as follows: 



- 204 where **X** _i_ and **X**<sup>�</sup> _c_ are the multivariate time trajectories of the _i_ -th spatial unit and of the 205 _c_ -th spatial medoid ( _c_ = 1 _, . . . , C_ ), respectively; _D_ ( _·, ·_ ) is the DTW dissimilarity measure 

- 206 for multivariate spatial time series; _m >_ 1 is the fuzziness parameter; _βk ≥_ 0 is the 

- 207 tuning parameter of the _k_ -th spatial information; _pkii′_ is the generic element of the ( _I × I_ ) 208 “proximity” matrix **P** _k_ ; _Cc_ is the set of the _C_ clusters, with the exclusion of cluster _c_ ; _uic_ 209 is the membership degree of the unit _i_ to the cluster _c_ . 210 The objective function in (4) is made up by two distinguished terms: 

- 211 _•_ the time dependent term (see section 2.3.1) 



- 212 _•_ the spatial dependent term 



213 

which is the sum of _K_ spatial penalty terms (see section 2.3.2). 

7 

214 The two terms (5) and (6) are computed over the same data range, i.e., over the same 215 observations. In the clustering process, one term could dominate the other depending on 216 the data at hand. The way in which both terms contribute to the clustering results will 217 be clarified in sections 2.3.1-2.3.2. 

218 The optimal iterative solution for the objective function in (4) is: 



219 As a final remark, the overall optimization of the objective function in (4) ensures that 220 the cohesion within clusters is maximized and that the spatial autocorrelation existing in 221 the data at hand is properly coped with, simultaneously, as it will be explained in the 222 following. 

223 

## _2.3.1. Time dependent term_ 

224 The time dependent term (5) is the within cluster dispersion due to the time-varying 225 features of multivariate trajectories. As observed in section 2.1, in this term the whole time 226 information is inherited by the Dynamic Time Warping measure, that takes into account 227 both the instantaneous and the variational features of the multivariate time trajectories. 228 When there are no spatial information, the time dependent term (5) coincides with the 229 Dynamic Time Warping Fuzzy _C_ -Medoids (DTW-FCMd) for multivariate time trajectories 230 introduced by D’Urso et al. (2018). 

## _2.3.2. Spatial dependent term_ 

- 231 _2.3.2. Spatial dependent term_ 232 The spatial dependent term (6) suitably allows the objective function to incorporate 233 different sources of spatial information. The term (6) is the sum of _K_ ( _K ≥_ 1) spatial 234 penalty terms (Pham, 2001; Coppi et al., 2010), one for each definition of proximity among 235 areas considered. In this way, the clustering method captures the information connected 236 to the different levels of proximity (multilevel proximity). For instance, we can consider 237 the simple case illustrated in Figure 2 in which 5 units, i.e. towns, and 2 macroarea, i.e. 238 valleys, are considered. In this specific case, two kinds of proximity can be defined: (i) 239 proximity among towns (level 1 proximity); belonging to the same valley (level 2 proximity). 240 Therefore, four different scenarios can be identified: 1) two towns ( _a_ 1 and _a_ 2) are close to 

- 241 each other (level 1 proximity) and they belong to the same valley (level 2 proximity); 2) 

- 242 two towns ( _a_ 1 and _b_ 1) are close to each other (level 1 proximity) but they do not belong 

- 243 to the same valley; 3) two towns ( _a_ 1 and _a_ 3) are not close to each other but they belong 244 to the same valley (level 2 proximity); 4) two towns ( _a_ 1 and _b_ 2) are not close to each other 

- 245 and they do not belong to the same valley. 

- 246 In each spatial penalty term two parameters are relevant, the proximity matrix **P** _k_ , and 247 the tuning parameter _βk_ . 

8 



<!-- Start of picture text -->
a 1 b 1<br>a 2<br>a 3 b 2<br><!-- End of picture text -->

Figure 2: Example of proximity among areas where _a_ 1, _a_ 2, _a_ 3, _b_ 1, and _b_ 2 are towns and the light green and dark green areas represent two valleys 

- 248 The role of the _k_ -th proximity matrix, **P** _k_ , is to increase the membership degree of unit 249 _i_ in cluster _c_ and, at the same time, to increase the membership degrees of the units that 250 are connected, in some way, to _i_ in cluster _c_ , while reducing these membership degrees 251 in the other clusters. We define this spatial smoothing as “proximity effect”, where, as 252 previously observed, the concept of proximity is vast enough to encompass different types of 253 connectivity between areas. The tuning parameter _βk_ must be set depending on the spatial 254 autocorrelation among data (see section 2.5 below). _βk_ could enhance the proximity effect 255 due to **P** _k_ if the spatial autocorrelation between units is high, e.g., if the features of a spatial 256 unit display a certain degree of concordance with those of its neighbours. Otherwise, _βk_ 257 could counterbalance, if not neutralise at all, the proximity effect, if there is relatively low 258 spatial autocorrelation between areas. Then, the greater the value of _βk_ , the greater is the 259 weight of the concept of proximity ascribed to it in the clustering process. Let say that 260 _β_ 1 corresponds to the distance between areas, and _β_ 2 to the belonging to the same macro261 area, then, if _β_ 1 _> β_ 2, “closeness” plays a major role than “belonging” in the optimization 262 process. 

- 263 As already observed, the choice of the value of _βk_ is data dependent. Coppi et al. 264 (2010) observed that the choice should be made according to a measure of a within cluster 265 spatial autocorrelation (see section 2.5), to avoid that the spatial smoothing induced by 266 the proximity matrix overcome the cluster separation. Indeed, an excessively high value 267 of one or more _βk_ ’s could constraint all neighbour units to be classified in one cluster, 268 regardless the features observed. A heuristic procedure for a custom-made choice of _βk_ ’s 

9 

- 269 is illustrated in section 4. 

- 270 Finally, it should be stressed that by combining **P** _k_ and _βk_ in the clustering process, 271 we are able to take into account also the spatial autocorrelation which is more informative 272 than the spatial proximity alone. 

- 273 _2.3.3. A remark on the use of spatial information_ 

- 274 As highlighted in the Introduction, in spatial clustering there are different approaches 275 to incorporate spatial information in a clustering framework. In particular, spatial infor276 mation can be represented in a clustering method by considering the contiguity/adjacencies 277 between each pair of territorial (spatial) units (Gordon, 1999). This information is usu278 ally formalized in the clustering method by means of contiguity/adjacencies constraints 279 or suitable spatial weights associated to distance measures. This approach is preferred in 280 hierarchical clustering (i.e. agglomerative) or in relational clustering where the distance 281 measure is taken for each pair of territorial units. In doing so the spatial information is 

- 282 represented algebraically by a squared matrix (called either contiguity matrix or spatial 283 matrix) associated to the squared distance matrix. Each element of this matrix represents 284 the territorial proximity between two units that can be represented by either dichotomous 285 values (0 or 1), indicating if the units are neighbouring or not, or quantitative values 286 representing the road distances or travel times. 

- 287 In the literature, another well-known approach used to incorporate spatial information 288 in the clustering procedure is to introduce a suitable penalty term in the objective function 289 used in the optimization procedure for clustering territorial units (see, e.g., Pham, 2001; **?** ; 290 Coppi et al., 2010). This approach is used in non-hierarchical framework (e.g. hard or fuzzy 291 _C_ -means clustering and hard or fuzzy partitioning around medoids procedures, as the hard 292 or fuzzy _C_ -medoids clustering), where the spatial information cannot be represented by 293 squared matrix. In fact, in these cases, the dimension of the distance matrix is rectangular 294 (the matrix contains values representing, e.g., the distance between each territorial unit 295 and each centroid or between each territorial unit and each medoid, where centroids and 296 medoids are the prototypes representing the clusters). This approach is quite common in 

- 297 the spatial clustering literature. As remarked by Pham (2001), “a classical approach to 298 incorporating spatial information is to penalize the [...] objective function [of the fuzzy 299 clustering] to constrain the behavior of the membership functions, similar to methods used 

- 300 in regularization and Markov random field (MRF) theory ( **?** ). This penalty can be used 

- 301 to discourage unlikely or undesirable configurations in the membership functions, such as 

- 302 a high membership value immediately surrounded by low values of the same class”. The 

- 303 Markov random field (MRF) theory has been used by **?** “which used standard first order 304 differences as a penalty to force membership values to be similar to neighbouring values. 305 The main problem with such a penalty function, however, is that it can drastically alter 

- 306 the characteristics of the membership function in an undesirable fashion. For example, first 

- 307 order differences will cause membership functions to be nearly piecewise constant. Second 

- 308 order differences will cause membership functions to be more smooth. However, depending 309 on the value of the [ _m_ ] parameter, this may contradict the desired characteristics of the 310 membership functions. [In our method], the objective function [see formula (4)] includes a 

10 

- 311 penalty term that is reminiscent of MRF priors but is consistent with the desired behavior 312 of the membership functions dictated by the value of the _m_ parameter” (Pham, 2001). As 313 remarked before, the use of penalty terms for taking into account the spatial proximity is 314 largely used in the literature, in different research areas (see, among others, **??????????** ). 315 Then, it is a consolidated methodological approach in the spatial clustering analysis. 316 Notice that, since our clustering method classify territorial units following a non317 hierarchical approach, we cannot consider the spatial information represented by conti318 guity or spatial measures (that compare pair of units) formalized as constraints or weights 319 associated to distance matrix (as in the hierarchical approach). In addition, since we con320 sider different levels of contiguity, considering different adjacency matrices as weights to 321 embed would considerably increase the complexity of the procedure. Nonetheless, as will 322 be remarked in the Conclusions, in the future we will explore the possibility to take into 323 account the spatial information in the clustering process following another clustering ap324 proach, i.e. the fuzzy relational method ( **?** Kaufman & Rousseeuw, 2005; D’Urso, 2015). 325 We will aslo investigate the computational and operational complexity of this alternative 326 clustering procedure (scalability, etc.). 

327 _2.4. Validity measure_ 

328 In general, internal validity measures provide useful guidelines in the identification of 329 the best partition (Handl et al., 2005; D’Urso, 2015). Suitable measures for fuzzy clustering 330 algorithm have been suggested by Xie & Beni (1991) and Campello & Hruschka (2006). 331 The Xie and Beni cluster validity index (Xie & Beni, 1991) is the ratio between com332 pactness and separation among clusters and it can be expressed as: 



333 where ( _p, q_ ) _∈{_ 1 _. . . . , C}_ . The smaller _XB_ , the more compact and separate are the 334 clusters. 

335 The Fuzzy Silhouette ( _FS_ ) index (Campello & Hruschka, 2006) is computed as the 336 weighted average of individual silhouettes width, _λi_ , (Kaufman & Rousseeuw, 2005), with 337 weights derived from the fuzzy membership matrix **U** = _{uic_ : _i_ = 1 _, . . . , I_ ; _c_ = 1 _, . . . , C}_ 338 as follows: 



339 Here, _ai_ is the average distance between the _i_ -th unit and the units belonging to the 340 cluster _p_ ( _p_ = 1,..., _C_ ) with which _i_ is associated with the highest membership degree; _bi_ is 341 the minimum (over clusters) average distance of the _i_ -th unit to all units belonging to the 342 cluster _q_ with _q̸_ = _p_ ; ( _uip − uiq_ )<sup>_α_</sup> is the weight of each _λi_ calculated upon **U** , where _p_ and _q_ 343 are, respectively, the first and second best clusters (accordingly to the membership degree) 

11 

- 344 to which the _i_ -th unit is associated; _α ≥_ 0 is an optional user defined weighting coefficient. 345 The traditional (crisp) Silhouette coefficients is obtained by setting _α_ = 0. The higher 346 the value of _FS_ , the better the assignment of the units to the clusters simultaneously 347 obtaining the minimisation of the intra-cluster distance and the maximisation of the inter348 cluster distance. 

- 348 

349 

## _2.5. Spatial autocorrelation_ 

- 350 In this paper, we introduce a new measure of spatial autocorrelation to assess the 351 post-cluster autocorrelation between units, the Fuzzy Moran ( _FM_ ) index. This index is a 352 multivariate fuzzy generalisation of the Moran’s index (Gittleman & Kot, 1990) and it is 353 a generalization of the spatial autocorrelation measure introduced by Coppi et al. (2010). 354 The idea of the _FM_ index is to compute the spatial autocorrelation between classified 355 units in which both the fuzzy membership matrix **U** and the spatial proximity matrices 356 **P** _k_ are considered. The _FM_ index is defined as follows: 



357 where **U** _c_ is the square diagonal matrix of order _I_ of the membership degrees of cluster _c_ ; 358 **X** ¯ is the centred “compromise” matrix (mean of the _T_ data matrices **X** _t_ ); **P** ˜ is the weighted 359 spatial matrix obtained as linear combination between the _K_ proximity matrices as follows 360 



361 where 0 _≤ wk ≤_ 1 and<sup>�</sup><sup>_K_</sup> _k_ =1<sup>_wk_= 1.The</sup><sup>_FM_index (as the Moran’s index) ranges between</sup> 

- 362 -1 and 1. A value of 1 indicates perfect positive spatial autocorrelation, i.e. neighbouring 363 units have similar values, 0 indicates no autocorrelation, i.e. units are spatially random 364 located, and -1 indicates perfect negative spatial autocorrelation, i.e. neighbouring units 365 have dissimilar values (P´aez & Scott, 2005). Thus, the higher the _FM_ value, the better 366 the geographical assignment of the units to the clusters. 

- 367 Moreover, the Fuzzy Moran’s index, as the Moran’s index, can be interpreted as a mea368 sure of spatial spill-over effect (Ma et al., 2015; Yang, 2012). In the literature, the spatial 369 spill-over effect is considered as the indirect or unintentional effects that a geographical 370 area exerts on other neighbour areas (Yang & Fik, 2014). A positive spill-over effect is 371 obtained when an area benefits of their neighbours influence due to the existence of spatial 372 externalities across area. 

372 

373 

## _2.6. Some comparative assessment_ 

374 Our proposal inherits all the advantages of the ingredients considered in the method375 ological framework. In particular, in a comparative assessment point of view, with respect 376 to some methods suggested in the literature we have the following evidences. 

12 

- 377 _•_ The fuzzy clustering methods proposed by D’Urso et al. (2018) show very good 378 performance for clustering units with time-varying information. However, when the 379 units are regions, geographical areas, etc., it is more useful to analyse this kind of units 380 by considering clustering methods capable to capture the territorial nature of the 381 units. To this purpose, the method proposed in this paper is able to cluster units not 382 only considering time information but also taking into account additional information 383 connected to spatial characteristics of the units. In particular, our method is able 384 to cluster territorial units considering explicitly in the objective function the spatial 385 information connected to the units—territorial proximity and spatial autocorrelation 386 (see sections 2.2 and 2.3.2). Notice that, the fuzzy clustering methods proposed by 387 D’Urso et al. (2018) could be applied to territorial units, but ignoring the territorial 388 information that characterizes this type of unit. However, this would represent a 389 relevant loss of information in the spatial analysis process. Furthermore, with respect 390 to the fuzzy clustering methods suggested by D’Urso et al. (2018) based on the 391 Euclidean distance, the proposed method inherits all the advantages of the DTW392 based dissimilarity measure (see, section 2.1). 

- 393 _•_ The Fuzzy _C_ -Means clustering method for spatial time series proposed by Coppi 394 et al. (2010) (Cross-Sectional Fuzzy _C_ -Means for Spatial-Temporal Trajectories, CS395 FCM-STT) is able to cluster territorial units with time-varying information. With 396 respect to this method our proposal has two more advantages inherited: (i) by the 397 kind of prototypes utilized in our method (i.e. medoids vs centroids); (ii) by the 398 characteristics of the spatial component considered in the objective function of the 399 proposed method. 

- 400 (i) With respect to the advantage connected to the kind of prototypes (i.e. medoids), 401 adopting PAM approach, the prototypes of each cluster (medoids) are territorial units 402 actually observed and not “virtual” territorial units like the “centroids” derived with 403 a Fuzzy _C_ -Means—as in the method suggested by Coppi et al. (2010). Overall, 404 having non-fictitious representative territorial units available makes interpreting the 405 obtained clusters easier, which is often very useful in geographical and territorial 406 applications. In fact, “in many clustering problems one is particularly interested 407 in a characterization of the clusters by means of typical or representative objects 408 [territorial units]. These are objects [territorial units] that represent the various 409 structural aspects of the set of objects [territorial units] being investigated. There can 410 be many reasons for searching for representative objects [territorial units]. Not only 411 can these objects [territorial units] provide a characterization of the clusters, but they 412 can often be used for further work or research, especially when it is more economical 413 or convenient to use a small set of _k_ objects [ _C_ territorial units in our case] instead 414 of the large set one started off with” (Kaufman & Rousseeuw, 2005). Furthermore, 

- 415 PAM clustering approach is slightly more robust than _C_ -Means approach (Garcia416 Escudero & Gordaliza, 1999; **?** ; Estivill-Castro & Yang, 2004; Kaufman & Rousseeuw, 417 2005), hence DTW-FCMd-STT is relatively more resistant to the presence of noise 418 in the data than CS-FCM-STT. 

13 

- 419 (ii) With respect to the advantages connected to spatial dependent term of the ob420 jective function, our spatial term is more general compared with the spatial term 421 considered in the method suggested by Coppi et al. (2010). In fact, as remarked in 

- 422 section 2.3.2, it is capable to consider different level of spatial proximity (multilevel 

- 423 proximity) and then it is more informative in a spatial point of view in the sense that 424 it is able to capture in deep the political and physical geographical characteristics 425 -e.g. administrative and economic features and geophysical and orographic nuances426 of the analysed territorial area. In this way, the spatial dependent term used in Coppi 427 et al. (2010) is a particular case of the term adopted in our method. See section 2.3.2 428 for more details. 

428 

429 

## **3. Illustration with simulated data** 

430 

   - _3.1. Simulation study 1_ 

- 431 In the following, a simulation study in which two contiguity matrices are considered for 432 simplicity, is presented. The aim of this exercise is to assess the sensitivity of the clustering 433 process to the contiguity matrices, according to the _k_ -th spatial parameters _βk_ (formula 434 4). 

- 435 An artificial data set is generated with two natural clusters and two units close to each 436 other and characterized by soft memberships to one of the two clusters. Two contiguity 437 matrices, one with contiguity only among the units within the natural clusters (including 438 the soft membership unit) and one including the contiguity between the soft membership 439 units as well, are generated. The aim of the simulation is to verify the decreasing of the 440 fuzzy membership degrees of the two soft membership units with respect to their natural 441 clusters and, eventually, even their memberships to the same cluster while increasing the 442 spatial penalty coefficient of the matrix including contiguity between them. For this reason, 443 the spatial penalty coefficients _β_ 1 and _β_ 2 range in (0 _,_ 8). 

- 444 The number of units, variables, and periods of time considered are _I_ = 8, _J_ = 2, and 445 _T_ = 6, respectively. In the contiguity matrix **P** 2, two sets of contiguous units are defined, 446 i.e. (1, 2, 3, 4) and (5, 6, 7, 8), whereas in **P** 1 the contiguity between units 4 and 5 is 447 added. The contiguity matrices **P** 1 and **P** 2 are the following: 

|||_u_1|_u_2|_u_3|_u_4|_u_5|_u_6|_u_7|_u_8<br>|
|---|---|---|---|---|---|---|---|---|---|
||<br>_u_1|1|1|1|1|0|0|0|0<br><br>|
||<br><br>_u_2|1|1|1|1|0|0|0|0<br><br><br>|
||<br><br>_u_3|1|1|1|1|0|0|0|0<br><br><br>|
|**P**1 =|<br><br><br>_u_4|1|1|1|1|1|0|0|0<br><br><br><br>|
||<br><br>_u_5|0|0|0|1|1|1|1|1<br><br><br>|
||<br><br>_u_6|0|0|0|0|1|1|1|1<br><br><br>|
||<br><br>_u_7|0|0|0|0|1|1|1|1<br><br><br>|
||<br>_u_8|0|0|0|0|1|1|1|1<br>|



448 

14 



449 The generation process of the dataset is summarized in Table 1. The defined clusters 450 are (1, 2, 3) and (6, 7, 8). Units 4 and 5 are characterized by a _fuzzy_ membership to 451 clusters (1, 2, 3) and (6, 7, 8), respectively. Going from data configuration 1) to data 452 configuration 4), we can note that units 4 and 5 are getting closer and closer (Table 1 and 453 Figure 3). 

|**Coi**|**nfiguration**|**units 1,2,3**|**unit 4**|**unit 5**|**units 6,7,8**|
|---|---|---|---|---|---|
|1)|_j_=1<br>_j_=2|_U_[0_._0_,_0_._5]<br>_U_[0_._0_,_0_._5]|_U_[0_._8_,_1_._0]<br>_U_[0_._8_,_1_._0]|_U_[1_._0_,_1_._2]<br>_U_[1_._0_,_1_._2]|_U_[1_._5_,_2_._0]<br>_U_[1_._5_,_2_._0]|
|2)|_j_=1|_U_[0_._0_,_0_._5]|_U_[0_._85_,_1_._0]|_U_[1_._0_,_1_._15]|_U_[1_._5_,_2_._0]|
||_j_=2|_U_[0_._0_,_0_._5]|_U_[0_._85_,_1_._0]|_U_[1_._0_,_1_._15]|_U_[1_._5_,_2_._0]|
|3|_j_=1|_U_[0_._0_,_0_._5]|_U_[0_._9_,_1_._0]|_U_[1_._0_,_1_._1]|_U_[1_._5_,_2_._0]|
|)|_j_=2|_U_[0_._0_,_0_._5]|_U_[0_._9_,_1_._0]|_U_[1_._0_,_1_._1]|_U_[1_._5_,_2_._0]|
|4|_j_=1|_U_[0_._0_,_0_._5]|_U_[0_._95_,_1_._0]|_U_[1_._0_,_1_._05]|_U_[1_._5_,_2_._0]|
|)|_j_=2|_U_[0_._0_,_0_._5]|_U_[0_._95_,_1_._0]|_U_[1_._0_,_1_._05]|_U_[1_._5_,_2_._0]|



Table 1: Data generation process for simulation study 1. Two clusters are generated from the data. Going from configuration 1) to configuration 4), units 4 and 5 are getting closer 

454 The membership degree obtained in the case of the fourth data configuration (see Table 455 1 and Figure 3) are reported in Table 2. By suitably tuning the values of _β_ 1 and _β_ 2, and 456 therefore the separate influence of the two contiguity matrices **P** 1 and **P** 2, we can see how 457 the two units 4 and 5 become more clearly separated, and then classified to the respective 458 clusters when _β_ 1 _< β_ 2, or, on the contrary, are classified in the same cluster, when _β_ 1 _> β_ 2. 459 For more details on the membership degrees and on performance results, see the Ap460 pendix Appendix A.1 to this paper. 

461 

## _3.2. Simulation study 2_ 

462 This simulation study is similar to that presented in section 3.1. We increased the 463 number of objects and of clusters, to show the performance of DTW-FCMd-STT in a 464 more complex environment. Similarly as in an simulation study 1, artificial data set is 465 generated with four natural clusters and four units close to each other characterized by 466 soft membership to one of the four clusters. Two contiguity matrices, one with contiguity 

15 



<!-- Start of picture text -->
1) 2)<br>0.0 0.5 1.0 1.5 2.0 0.0 0.5 1.0 1.5 2.0<br>j=1 j=1<br>3) 4)<br>0.0 0.5 1.0 1.5 2.0 0.0 0.5 1.0 1.5 2.0<br>j=1 j=1<br>2.0 2.0<br>1.5 1.5<br>j=2 1.0 j=2 1.0<br>0.5 0.5<br>0.0 0.0<br>2.0 2.0<br>1.5 1.5<br>j=2 1.0 j=2 1.0<br>0.5 0.5<br>0.0 0.0<br><!-- End of picture text -->

Figure 3: Data generation process for simulation study 1. Two clusters are generated from the data. Going from configuration 1) to configuration 4), units 4 and 5 are getting closer 

|(_β_1_, β_2)|(0_,_|0)|(4_,_|0)|(0_,_|4)|(8_,_|0)|(0_,_|8)|
|---|---|---|---|---|---|---|---|---|---|---|
|cluster|1|2|1|2|1|2|1|2|1|2|
|1|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|
|2|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|
|3|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|
|4|0.6271|0.3729|0.6853|0.3147|0.6689|0.3311|0.7168|0.2832|0.7051|0.2949|
|5|0.4874|0.5126|0.5256|0.4744|0.4603|0.5397|0.5169|0.4831|0.4138|0.5862|
|6|0.0000|1.0000|0.0000|1.0000|0.0001|0.9999|0.0000|1.0000|0.0001|0.9999|
|7|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|
|8|0.0003|0.9997|0.0001|0.9999|0.0004|0.9996|0.0001|0.9999|0.0004|0.9996|



Note: Medoids’ membership degrees are in bold. 

Table 2: Membership degrees for simulation study 1 obtained under the data configuration 4), according to different combinations of _β_ 1 and _β_ 2 

16 

- 467 only among the units within the natural clusters (including the soft membership unit) and 

- 468 one including the contiguity among the soft membership units as well, are generated. The 

- 469 aim of the simulation is to verify the decreasing of the fuzzy membership degree of the 470 four soft membership units to the natural clusters and eventually even their membership 471 to the same cluster while increasing the spatial penalty coefficient of the matrix including 472 contiguity among them. To this end, the spatial penalty coefficients _β_ 1 and _β_ 2 range in 473 (0 _,_ 20). 

- 474 The number of units, variables, and periods of time considered are _I_ = 16, _J_ = 2, and 475 _T_ = 6, respectively. In the first contiguity matrix ( **P** 2), the contiguous units are (1, 2, 3, 476 4), (5, 6, 7, 8), (9, 10, 11, 12) and (13, 14, 15, 16), whereas in **P** 1 the contiguity among 477 units 4, 5, 12, 13 is added. 

- 478 The generation process of the dataset is summarized in Table 3. The defined clusters 479 are (1, 2, 3), (6, 7, 8), (9, 10, 11), (14, 15, 16). Units 4, 5, 12, 13 are characterized by 480 a _fuzzy_ membership to clusters (1, 2, 3), (6, 7, 8), (9, 10, 11), (14, 15, 16), respectively. 481 Going from data configuration 1) to data configuration 4) units 4, 5, and 12, 13 are getting 482 closer and closer, respectively (Table 3 and Figure 4). 

|**Configuration**|**units 1,2,3**|**unit 4**|**unit 5**|**units 6,7,8**<br>|**units 9,10,11**|**unit 12**|**unit 13**|**units 14,15,16**|
|---|---|---|---|---|---|---|---|---|
|1) <sup>_j_=1</sup><br>_j_=2|_U_[0_._0_,_0_._5]<br>_U_[0_._0_,_0_._5]|_U_[0_._6_,_0_._7]<br>_U_[0_._6_,_0_._7]|_U_[0_._6_,_0_._7]<br>_U_[1_._3_,_1_._4]|_U_[0_._0_,_0_._5]<br>_U_[1_._5_,_2_._0]|_U_[1_._5_,_2_._0]<br>_U_[1_._5_,_2_._0]|_U_[1_._3_,_1_._4]<br>_U_[1_._3_,_1_._4]|_U_[1_._3_,_1_._4]<br>_U_[0_._6_,_0_._7]|_U_[1_._5_,_2_._0]<br>_U_[0_._0_,_0_._5]|
|2 <sup>_j_=1</sup>|_U_[0_._0_,_0_._5]|_U_[0_._7_,_0_._8]|_U_[0_._7_,_0_._8]|_U_[0_._0_,_0_._5]|_U_[1_._5_,_2_._0]|_U_[1_._2_,_1_._3]|_U_[1_._2_,_1_._3]|_U_[1_._5_,_2_._0]|
|) <br>_j_=2|_U_[0_._0_,_0_._5]|_U_[0_._7_,_0_._8]|_U_[1_._2_,_1_._3]|_U_[1_._5_,_2_._0]|_U_[1_._5_,_2_._0]|_U_[1_._2_,_1_._3]|_U_[0_._7_,_0_._8]|_U_[0_._0_,_0_._5]|
|3) <sup>_j_=1</sup><br>_j_=1|_U_[0_._0_,_0_._5]<br>_U_[0_._0_,_0_._5]|_U_[0_._8_,_0_._9]<br>_U_[0_._8_,_0_._9]|_U_[0_._8_,_0_._9]<br>_U_[1_._1_,_1_._2]|_U_[0_._0_,_0_._5]<br>_U_[1_._5_,_2_._0]|_U_[1_._5_,_2_._0]<br>_U_[1_._5_,_2_._0]|_U_[1_._1_,_1_._2]<br>_U_[1_._1_,_1_._2]|_U_[1_._1_,_1_._2]<br>_U_[0_._8_,_0_._9]|_U_[1_._5_,_2_._0]<br>_U_[0_._0_,_0_._5]|
|4) _j_=1<br>_j_=2|_U_[0_._0_,_0_._5]<br>_U_[0_._0_,_0_._5]|_U_[0_._9_,_1_._0]<br>_U_[0_._9_,_1_._0]|_U_[0_._9_,_1_._0]<br>_U_[1_._0_,_1_._1]|_U_[0_._0_,_0_._5]<br>_U_[1_._5_,_2_._0]|_U_[1_._5_,_2_._0]<br>_U_[1_._5_,_2_._0]|_U_[1_._0_,_1_._1]<br>_U_[1_._0_,_1_._1]|_U_[1_._0_,_1_._1]<br>_U_[0_._9_,_1_._0]|_U_[1_._5_,_2_._0]<br>_U_[0_._0_,_0_._5]|



Table 3: Data generation process for simulation study 2. Four clusters are generated from the data. Going from configuration 1) to configuration 4), units 4, 5, and 12, 13 are getting closer 

483 Once again, according to the combination of _β_ 1 and _β_ 2, the _fuzzy_ units get more sepa484 rated when _β_ 1 _< β_ 2, while eventually are classified in the same cluster when _β_ 1 _> β_ 2. 485 For more details on the membership degrees and on performance results, see the Ap486 pendix Appendix A.2 to this paper. 

487 _3.3. Simulation study 3_ 

- 488 In this simulation study we highlight two main features of the proposed clustering 489 method: 

- 490 1. the capability to deal with time series of different length; 491 2. the capability to fully exploit spatial information. 

492 We simulated a dataset of 20 three-variate ( _I_ = 20 _, J_ = 3) time series of length ranging 493 from _T_ = 6 to _T_ = 10. The data generation process yielded to three partially overlapping 494 clusters ( _C_ = 3) of size 10, 5 and 5, respectively (see Figure 5). 

17 



<!-- Start of picture text -->
1) 2)<br>0.0 0.5 1.0 1.5 2.0 0.0 0.5 1.0 1.5 2.0<br>j=1 j=1<br>3) 4)<br>0.0 0.5 1.0 1.5 2.0 0.0 0.5 1.0 1.5 2.0<br>j=1 j=1<br>2.0 2.0<br>1.5 1.5<br>j=2 1.0 j=2 1.0<br>0.5 0.5<br>0.0 0.0<br>2.0 2.0<br>1.5 1.5<br>j=2 1.0 j=2 1.0<br>0.5 0.5<br>0.0 0.0<br><!-- End of picture text -->

Figure 4: Data generation process for simulation study 2. Four clusters are generated from the data. Going from configuration 1) to configuration 4), units 4, 5, and 12, 13 are getting closer 

18 



<!-- Start of picture text -->
x y z<br>Cluster 1 Cluster 2 Cluster 3<br><!-- End of picture text -->

Figure 5: Simulated data for simulation study 3. Data are generated to be classified into three partially overlapping clusters. Time series belonging to different clusters are depicted with different colours and line types 

- 495 As for the spatial dependence, we generated two proximity matrices, **P** 1 and **P** 2, illus496 trated in Figure 6. A black square indicate that there is some kind of proximity between _i_ 497 and _j_ . The two matrices refer to different notions of proximity, which are closely related to 498 those observed in the empirical application: **P** 1 refers to a situation in which two units are 499 neighbours if they share a border; **P** 2 represents a situation in which proximity is due to 500 the fact that belong to the same macro-area, even if they are not neighbour. Furthermore, 501 each macro-area corresponds to a different cluster. By observing **P** 1 and **P** 2, there are some 502 units that are neighbours even if they belong to different macro-areas, and some units that 503 belong to the same macro-area but they are not neighbour. Finally, the parameters _β_ 1 and 504 _β_ 2 are set to 0 or 1.8, depending on how the spatial information is exploited. 505 The purpose of the present simulation is to show the capability of DTW-FCMd-TSS 506 to individuate the three clusters, even if data are rather noise, by exploiting the spatial 507 information. For comparison’s sake we consider four cases, described in Table 4. The first 508 case refers to DTW-FCMd clustering method described in D’Urso et al. (2018). The second 509 and the third cases are particular instances of the proposed DTW-FCMd-STT, in which 510 we exploited only a part of the spatial information provided by the proximity matrices _P_ 1 511 and _P_ 2 (see Figure 6). In the fourth case, the spatial information is fully exploited. 512 To evaluate the classification capability, we used the Fuzzy Rand Index ( _FRI_ ) proposed 513 by H¨ullermeier et al. (2012), comparing the fuzzy partition obtained with the theoretical 514 crisp reference partition. The closer _FRI_ is to 1, the closer the fuzzy partition to the 515 theoretical crisp reference partition. The results of the simulation are reported in the last 516 column of Table 4. DTW-FCMd provides a partition that takes into account only the 517 time dimension, which is rather fuzzy as explained, thus explaining the relative low value 518 of _FRI_ (case A). Exploiting only a part of the spatial information slightly enhances the 519 classification capability of DTW-FCMd-STT with respect to DTW-FCMd (cases B and 

19 



<!-- Start of picture text -->
P 1 P 2<br>20<br>15<br>10<br>5<br>0<br>0 5 10 15 20 0 5 10 15 20<br><!-- End of picture text -->

Figure 6: Proximity matrices – black squares indicate the proximity between two generic units (simulation study 3) 

|Case|Method|_P_1|_P_2|_β_1|_β_2|_FRI_|
|---|---|---|---|---|---|---|
|A|DTW-FCMd|No|No|0.0|0.0|0.720|
|B|DTW-FCMd-STT|Yes|No|1.8|0.0|0.734|
|C|DTW-FCMd-STT|No|Yes|0.0|1.8|0.741|
|D|DTW-FCMd-STT|Yes|Yes|1.8|1.8|0.985|



Table 4: Fuzzy Rand Indices for simulation study 3, according to different clustering models (row wise) and different settings of spatial parameters (column wise) 

20 

- 520 C). On the contrary, by exploiting the whole spatial information, the clustering method 521 is capable to correctly identify the clustering structure of the data at hand, properly in522 corporating the spatial information (case D). This evidence is further corroborated by the 523 membership degrees obtained in the four cases, illustrated by the ternary plots<sup>1</sup> reported 524 in Figure 7. In the ternary plot, every point represents the membership degrees of the 525 corresponding time series in the three cluster. The more a point is close to a vertex of 526 the triangle, the less uncertain is the assignment of the time series to the corresponding 527 cluster. 

527 



<!-- Start of picture text -->
Scenario 1 Scenario 2<br>G 100 G 100<br>G G G G 80 GG GG GG 80<br>GG 60 G 60<br>GG G G GG 40 GG G G GG 40<br>G 20 20<br>G G G G G G G G<br>Cluster 3 Cluster 3<br>Scenario 3 Scenario 4<br>G 100 GG G G G 100<br>G GGG GG G 8060 8060<br>G<br>GG G G 40 40<br>20 20<br>G G G G G GGG G GG G G G G G<br>Cluster 3 Cluster 3<br>20 20<br>40 40<br>60 60<br>Cluster 1 Cluster 2 Cluster 1 Cluster 2<br>80 80<br>100 100<br>20 40 60 80 100 20 40 60 80 100<br>20 20<br>40 40<br>60 60<br>Cluster 1 Cluster 2 Cluster 1 Cluster 2<br>80 80<br>100 100<br>20 40 60 80 100 20 40 60 80 100<br><!-- End of picture text -->

Figure 7: Membership degrees (simulation study 3) 

528 As a final word, it should be stressed that the purpose of the present simulation is to 529 clarify how the spatial information is embedded into the proposed clustering method. 

530 _3.4. Simulation study 4_ 

531 For this simulation study, we partly replicated a simulation study proposed by D’Urso 532 (2005a) and D’Urso et al. (2018) with an artificial dataset characterised by three well533 separated clusters of four, three, and three multivariate time trajectories, respectively, and 534 one outlier time trajectory (Figure 8). The length of each time series simulated is _T_ = 6. 535 The proximity matrix in Figure 9 represents the spatial component that has been included 536 in this simulation study. Notice that a black square indicates proximity between units _i_ 537 and _i_<sup>_′_</sup> , while a red square indicates proximity between an outlier and a generic unit. 538 Being the time series of the same length and having added only one proximity matrix, 539 DTW-FCMD (D’Urso et al., 2018), our proposed clustering method (DTW-FCMd-STT), 540 CS-FCM (D’Urso, 2005a), and CS-FCM-STT (Coppi et al., 2010) are fully comparable. 

> 1The ternary plots have been produced by means of the R package `ggtern` (Hamilton & Ferry, 2018). 

21 



<!-- Start of picture text -->
cluster 1 cluster 2 cluster 3 outlier<br><!-- End of picture text -->

Figure 8: Simulated data for simulation study 4. Data are generated to be classified into three well separated clusters and one outlier time series. Time series belonging to different clusters and the outliers are depicted with different colours and line types 

22 



<!-- Start of picture text -->
9<br>6<br>3<br>3 6 9<br><!-- End of picture text -->

Figure 9: Proximity matrix – black squares indicate the proximity between two generic units: red squares indicate the proximity between the outlier and the corresponding unit (simulation study 4) 

23 

|Case|Method|Outlier|Spatial<br>information|_FRI_|
|---|---|---|---|---|
|A|DTWFCMd|No|No|0.984|
|B|-|Yes|No|0.797|
|C|DTWFCMdSTT|No|Yes|0.978|
|D|--|Yes|Yes|0.978|
|E|CSFCM|No|No|0.990|
|F|-|Yes|No|0.780|
|G|CSFCMSTT|No|Yes|0.948|
|H|--|Yes|Yes|0.761|



Table 5: Fuzzy Rand Indices for simulation study 4, according to different clustering models (row wise) and to the presence of spatial information and/or the outlier time series (column wise) 

- 541 Therefore, the simulation study is aimed to compare the classification capability of the 542 above mentioned methods. Implicitly, we also compare DTW-FCMd-STT and CS-FCM543 STT in the way they exploit the spatial information, in particular in the presence of a slight 544 disturbance, given by the outlier time series. The value of _β_ for both DTW-FCMd-STT 545 and CS-FCM-STT has been set to 1. 

- 545 546 In Table 5, _FRI_ values for the different cases examined are reported. As expected, 547 when the outlier time series is dropped from data, all clustering methods display a very 548 good clustering performance. On the contrary, only DTW-FCMD-STT is able to resist to 549 the presence of one outlier in the dataset. 

- 550 

## **4. Illustration with economic data** 

551 

## _4.1. Study data_ 

- 552 In this analysis, we consider annual tourist arrivals in the municipalities located in 553 South-Tyrol region (Northern Italy) collected by ASTAT (the local institute of statistics) 554 from 2008 to 2014. Given a geographic region having various localities as possible tourist 555 attractions, we aim at identifying agglomerations of cities characterised by a common trend 556 of the tourist flows over time taking into account the particular geographical and political 557 underlined structure. South–Tyrol is in fact a tourist destination characterised by 116 558 municipalities grouped into eight administrative districts that follow the geomorphology of 559 the region (see Figure 10). 

- 560 Therefore, each municipality is characterised by two spatial information: whether two 

- 561 units are contiguous or not; whether two units belong to the same district or not. In 562 this paper, each municipality is described by the annual time series on tourist flows from 563 the two main markets, i.e. Germany and Italy (domestic tourists). Table 6 shows the 564 descriptive characteristics of the two time series highlighting the high variability of arrivals 565 among municipalities in each year observed. 

24 



Figure 10: South–Tyrol region 

|Year|Me<br>Germany|an<br>Italy|S<br>Germany|D<br>Italy|MIN<br>Germany|Italy|MA<br>Germany|X<br>Italy|
|---|---|---|---|---|---|---|---|---|
|2008|19843.34|18198.87|20058.15|25493.66|0|0|103026|109185|
|2009|20334.71|18849.07|20735.57|26094.45|0|0|106228|113199|
|2010|21005.07|18997.12|21771.90|26757.23|0|2|111202|115211|
|2011|21901.66|18952.86|22375.17|26338.25|0|2|114095|112591|
|2012|23066.78|18774.24|23464.45|25751.07|0|2|117825|113070|
|2013|23300.02|18188.68|23779.26|25245.33|0|3|117064|110082|
|2014|23889.45|18024.78|23973.20|24675.21|0|0|111843|111070|



Table 6: Descriptive statistics of annual tourist arrivals from Germany and Italy 

25 

566 As highlighted in Figure 11, units are spatially autocorrelated, especially with regards 567 to domestic tourists who are mainly grouped in Val Pusteria (East part of the region). 



Figure 11: Average annual tourist flows 

568 By means of the suggested DTW-FCMd-STT clustering algorithm with spatial penalty 569 terms, we have the opportunity to: 1) identify agglomerations of cities characterised by 570 similar tourist arrival trends, by considering units’ geographical proximity and district 571 memberships; 2) recognise the medoid of each agglomeration, i.e. the municipality that 572 characterises each agglomeration and that can be considered as the representative touristic 573 municipality (in statistical terms) of a given sub-region. 

- 574 _4.2. Clustering results_ 

575 The optimal iterative solution is obtained by solving the DTW-FCMd-STT algorithm 576 with the Lagrangian multipliers method where: 

- 577 (1) the fuzziness parameter has been fixed to _m_ = 1 _._ 5 (Kamdar & Joshi, 2000); 

- 578 (2) the optimal number of clusters _C_ of the DTW-FCMd-STT algorithm without penalty 579 terms has been identified by means of the fuzzy cluster validity measures presented in 580 section 2.4; 

- 581 (3) the values of the two spatial penalty coefficients (i.e. _β_ 1 and _β_ 2) have been selected 582 in order to maximize the multivariate spatial autocorrelation of the whole area (with583 out considering the possible clustering structure) when both proximity matrices are 584 considered. 

- 585 Figure 12 summarises the values of the _FS_ and _XB_ indices calculated for any partition 586 _C_ from 2 to 9 when the spatial penalty terms are not included in the WTD-FCMd clustering 587 algorithm. The trajectories of the two indices suggest that the best partitions are _C_ = 2 588 followed by the four and six clusters partitions. 

589 The weighted multivariate spatial autocorrelation of the whole area has been computed 590 by means of equation 10 imposing **X**̄equals to the identity matrix. The weighting spatial 591 matrix **P**̃is computed through equation 11 fixing _K_ = 2: 

**P** ˜ = _w_ 1 **P** 1 + _w_ 2 **P** 2 

26 



<!-- Start of picture text -->
G<br>G<br>GG G<br>G<br>G GG GG<br>G G G G<br>GG<br>G<br>GG<br>FS<br>GG XB<br>2 3 4 5 6 7 8 9<br>Number of clusters<br>1.68<br>1.48<br>1.28<br>1.08<br>Validity index 0.88<br>0.68<br>0.48<br>0.28<br>0.08<br><!-- End of picture text -->

Figure 12: _FS_ and _XB_ validity index values for each cluster partition _C_ from 2 to 9 

592 where **P** 1 is a non-negative (116 _×_ 116) data matrix, whose generic entry _p_ 1 _ii′_ can be 593 interpreted as the spatial proximity between the _i_ -th and _i_<sup>_′_</sup> -th units ( _i, i_<sup>_′_</sup> = 1 _, . . . ,_ 116), **P** 2 594 is another non-negative (116 _×_ 116) data matrix, whose generic entry _p_ 2 _ii′_ describes whether 595 the _i_ -th and _i_<sup>_′_</sup> -th units belong to the same district or not, _w_ 1 = 1 _− w_ 2 is the parameter 596 to be identified in order to maximize the weighted multivariate spatial correlation. Once 597 the optimal value of _w_ 1, i.e. _w_ 1<sup>_∗_,isidentified,wesuggesttodefinethetwospatialpenalty</sup> _<u>β</u>_ <u>1</u> 598 parameters, i.e. _β_ 1 and _β_ 2, such as _w_ 1 = Consequently, the best combination _β_ 1+ _β_ 2<sup>.</sup> 599 of _β_ 1 and _β_ 2 will be the one that allows to obtain the closer value to _w_ 1<sup>_∗_.Inthisway</sup> 600 we guarantee that the higher _w_ 1, the higher _β_ 1, i.e. the two parameters related to the 601 same proximity matrix **P** 1 go on the same direction. In this study, the maximum value 602 of the weighted multivariate spatial autocorrelation for the whole area is 0 _._ 21, indicating 603 a positive spatial autocorrelation between observed municipalities in inbound tourist from 604 Germany and domestic tourist flows, and _w_ 1<sup>_∗_= 0</sup><sup>_._68,asrepresentedinFigure13.</sup> 605 In the following, we will concentrate our attention on the four-clusters and six-clusters 606 solutions. In fact, from a managerial and practical perspective, the two-clusters is not an 607 appealing solution since it is not generally informative and useful to draw new policies and 608 strategies. 

609 Fixing _C_ = 4, the best combination of _β_ 1 and _β_ 2, i.e. the one that allows to maximize 610 the weighted multivariate spatial autocorrelation, is _β_ 1 = 0 _._ 01 and _β_ 2 = 0 _._ 005, which 611 allows to obtain a fairly high spatial autocorrelation between geographical units ( _FM_ = 612 0 _._ 50). Comparing the final 4 clusters obtained with and without the two spatial proximity 613 matrices, it emerges that the spatial information allows making small adjustments to the 614 membership degrees of the final matrix but not severe changes in the final fuzzy cluster 615 partition. 

27 



<!-- Start of picture text -->
G<br>0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0<br>Spatial weight w1<br>0.20<br>0.18<br>0.16<br>0.14<br>0.12<br>0.10<br>0.08<br>0.06<br>Multivariate spatial autocorrelation<br>0.04<br>0.02<br>0.00<br><!-- End of picture text -->

Figure 13: Values of the multivariate spatial autocorrelation of the whole area when proximity matrices are considered 

616 Conversely, when _C_ = 6 the best combination of _β_ 1 and _β_ 2 is _β_ 1 = 0 _._ 61 and _β_ 2 = 0 _._ 32, 617 which allows to obtain a fairly high spatial autocorrelation between geographical units 618 ( _FM_ = 0 _._ 47). As in the previous configuration, the proximity between areas is more 619 relevant than the belonging to the same district. Figure 14 compares the membership 620 degrees of each unit computed using DTW-FCMd-STT with and without penalty terms. 621 The most evident changes, both in terms of intensity and frequency, are observable in 622 cluster 1, 4, and 5. A similar conclusion can be reached observing the fuzzy cluster size, 623 i.e. the sum of membership degrees per cluster, represented in Table 7. This measure is 624 a proxy of the cluster size usually gather from crisp algorithm and it allows to spot both 625 niches (as cluster 2 and 6) and bigger clusters (as cluster 4 and 5). Overall, cluster 1, 4, 626 and 5 are the biggest clusters that highlight also the biggest changes. 

||1|2|3|4|5|6|
|---|---|---|---|---|---|---|
|Without spatial terms|10.7047|6.22686|9.02877|60.9413|22.6855|6.41291|
|With spatial terms|11.5986|6.19582|9.04499|61.2298|21.5608|6.37000|



Table 7: Sum of the membership degrees by cluster 

627 For a deeper understanding and interpretation of the differences between the results 628 of the two clustering algorithms, the membership degrees of each town/village, along with 629 the medoids of each cluster, are represented in Figure 15. 

629 the medoids of each cluster, are represented in Figure 15. 630 The final membership degrees to cluster 1, 4, and 5 obtained excluding and including 631 the penalty terms are compared to point out the most relevant changes. It is worthy of 

28 



<!-- Start of picture text -->
CL1 CL2 CL3<br>G GG G GG GG G GG G G<br>G<br>G G<br>G G G<br>G G<br>G G G G G GG<br>G G<br>G<br>GGGG G G GGG G G GGGGGG G G G G G GG G G G G GG G G GG GG GG GGGG<br>0.0 0.2 0.4 0.6 0.8 1.0 0.0 0.2 0.4 0.6 0.8 1.0 0.0 0.2 0.4 0.6 0.8 1.0<br>CL4 CL5 CL6<br>G GG GG GGG G G GGGGG G GGGG GG GGGGGG GGGG GGG G G<br>GG GG G<br>G<br>G GG<br>G<br>G G G G G G<br>G GG GGG G<br>G G GG G G GGG G GGGG G G GGG G GG GG GG G G GGG GGG GGG G GG G G G G GG G<br>0.0 0.2 0.4 0.6 0.8 1.0 0.0 0.2 0.4 0.6 0.8 1.0 0.0 0.2 0.4 0.6 0.8 1.0<br>With spatial penalty terms With spatial penalty terms With spatial penalty terms<br>1.0 1.0 1.0<br>0.8 0.8 0.8<br>0.6 0.6 0.6<br>0.4 0.4 0.4<br>0.2 0.2 0.2<br>Without spatial penalty terms<br>0.0 0.0 0.0<br>1.0 1.0 1.0<br>0.8 0.8 0.8<br>0.6 0.6 0.6<br>0.4 0.4 0.4<br>0.2 0.2 0.2<br>Without spatial penalty terms<br>0.0 0.0 0.0<br><!-- End of picture text -->

Figure 14: Comparing unit membership degrees to each cluster obtained using DTW-FCMd-STT with and without spatial terms 

632 notice that the inclusion of the penalty terms in the clustering algorithm does not force 633 final clusters to be made by neighbours town/village or to recall the districts. The change 634 in the medoid of cluster 1 is the most noticeable and important change observable. This 635 result have important practical consequences when policies and strategies are made at an 636 aggregate (medoid) level instead of at a municipality (geographical unit) level. 

- 636 aggregate (medoid) level instead of at a municipality (geographical unit) level. 637 For instance, marketing and promotional strategies to attract and host domestic or 638 German tourists will be different depending on the decision to include or not the penalty 639 terms (see Figure 16a). Furthermore, in Figure 16b the average cluster time series of the 640 tourist flows coming from Germany and Italy are represented. Tourist flows are unchanged 641 (domestic tourist) or slightly change (tourist from Germany) for cluster 2, 3, and 6, while 642 the remaining clusters present more consistent variations, especially for tourists coming 643 from Germany. 

643 from Germany. 644 Therefore, due to the particular geographical and political structure of the region, 645 ignoring the two proximity levels may lead to incorrect results and policies. 

### 646 

## **5. Conclusions** 

647 In this paper, the Dynamic Time Warping Fuzzy _C_ -Medoids for Spatial-Temporal Tra648 jectories (DTW-FCMd-STT) clustering algorithm with penalty terms, a new clustering 649 algorithm for the classification of units described by both multivariate time series and spa650 tial information, has been introduced. In particular, the main aim of this study is to present 651 a multivariate generalisation of the Coppi et al. (2010) clustering algorithm by 1) adopting 652 a more flexible distance measure, the DTW dissimilarity measure, and 2) extending the 

29 





<!-- Start of picture text -->
(a) Without spatial terms<br><!-- End of picture text -->



<!-- Start of picture text -->
(b) With spatial terms<br><!-- End of picture text -->

Figure 15: DTW-FCMd-STT without (on the left) and with (on the right) spatial terms when _C_ = 6 

30 

Figure 16: Medoids time series (16a) and weighted average arrivals by cluster (16b) 



<!-- Start of picture text -->
Medoids: Arrival from Germany Arrival from Italy<br>without penalty term with penatly term<br>CL1 CL4<br>CL2 CL5<br>CL3 CL6<br>2008 2009 2010 2011 2012 2013 2014 2008 2009 2010 2011 2012 2013 2014<br>(a)<br>Average by clusters: Arrival from Germany Arrival from Italy<br>without penalty term with penatly term<br>CL1 CL4<br>CL2 CL5<br>CL3 CL6<br>2008 2009 2010 2011 2012 2013 2014 2008 2009 2010 2011 2012 2013 2014<br>80213<br>63327<br>60213<br>48327<br>40213 33327<br>Average tourists flow<br>18327<br>20213<br>5213 3327<br>5985 6377<br>5385<br>5177<br>4785<br>3977<br>4185<br>2777<br>Average tourists flow 3585<br>2985 1577<br>2385 677<br><!-- End of picture text -->

(b) 

31 

- 653 possibility to classify units on which either different kinds or different levels of proximity 654 are identifiable. Furthermore, a new weighted multivariate spatial autocorrelation index 655 to evaluate the autocorrelation of the final fuzzy partition, i.e. the Fuzzy Moran’s index, 656 has been defined and presented. 

- 657 Different simulation studies and a real dataset drawn by the tourism field have been 658 presented to illustrate the usefulness and effectiveness of the suggested clustering method 659 for spatial-temporal series. In particular, the findings of the simulation studies describe 660 the sensitivity of the DTW-FCMd-STT clustering algorithm to changes in the proxim661 ity matrices. The application to the real case study shows that the DTW-FCMd-STT 662 algorithm may help in the identification of groups that are spatially close, making more 663 appealing the applicability of the results of the cluster analysis. Furthermore, the Fuzzy 664 Moran’s index reveal that a fairly high spatial autocorrelation between geographical units 665 exists. Consequently, this result also indicate the presence of a positive spill-over effect 666 among municipalities, i.e. one municipality’s tourism industries affects the tourism flows 667 of neighbours municipalities due to the existence of spatial externalities. 

- 668 Finally, it is worth exploring also the possibility of obtaining more robust version of 669 the proposed clustering algorithm, in order to cope with the presence of noise both in the 670 time and in the spatial dimensions. 

## 671 **Acknowledgment** 

- 672 The authors thank the Editor and the referees for their useful comments and suggestions 673 which helped to improve the quality and presentation of this manuscript. 

## 674 **References** 

- 675 Ahmed, M. N., Yamany, S. M., Mohamed, N., Farag, A. A., & Moriarty, T. (2002). A modified fuzzy c- 676 means algorithm for bias field estimation and segmentation of mri data. _IEEE Transactions on Medical_ 677 _Imaging_ , _21_ , 193–199. 

- 678 Alonso, A., & Maharaj, E. (2006). Comparison of time series using subsampling. _Comput. Stat. Data_ 679 _Anal._ , _50_ , 2589–2599. 

- 680 Basford, K., & McLachlan, G. (1985). The mixture method of clustering applied to three-way data. _J._ 681 _Classification_ , _2_ , 109–125. 

- 682 Bazin, P.-L., & Pham, D. L. (2007). Topology-preserving tissue classification of magnetic resonance brain 683 images. _IEEE Transactions on Medical Imaging_ , _26_ , 487–496. 

- 684 Begum, N., Ulanova, L., Wang, J., & Keogh, E. (2015). Accelerating dynamic time warping clustering with 685 a novel admissible pruning strategy. In _Proceedings of the 21th ACM SIGKDD International Conference_ 686 _on Knowledge Discovery and Data Mining_ (pp. 49–58). ACM. 

- 687 Berndt, D. (1994). Using Dynamic Time Warping to find patterns in time series. In _AAAI-94 Workshop_ 688 _on Knowledge Discovery in Databases_ . 

32 

- 689 Bezdek, J. (1981). _Pattern Recognition with Fuzzy Objective Function Algorithms_ . Norwell, MA, USA: 690 Kluwer Academic. 

- 691 Birant, D., & Kut, A. (2007). ST-DBSCAN: An algorithm for clustering spatial-temporal data. _Data_ 692 _Knowl Eng._ , _60_ , 208–221. 

- 693 Caiado, J., & Crato, N. (2010). Identifying common dynamic features in stock returns. _Quantitative_ 694 _Finance_ , _10_ , 797–807. 

- 695 Caiado, J., Crato, N., & Pe˜na, D. (2009). Comparison of times series with unequal length in the frequency 696 domain. _Communications in Statistics - Simulation and Computation_ , _38_ , 527–540. 

- 697 Caiado, J., Crato, N., & Pe˜ _n_ a, D. (2006). A periodogram-based metric for time series classification. 698 _Computational Statistics & Data Analysis_ , _50_ , 2668–2684. 

- 699 Caiado, J., Maharaj, E. A., & D’Urso, P. (2015). Time series clustering. In C. Hennig, M. Meila, 700 F. Murtagh, & R. Rocci (Eds.), _Handbook of Cluster Analysis_ (pp. 241–264). Chapman and Hall/CRC. 

- 701 Campello, R. J., & Hruschka, E. R. (2006). A fuzzy extension of the silhouette width criterion for cluster 702 analysis. _Fuzzy Sets and Systems_ , _157_ , 2858–2875. 

- 703 Castagno, R., Ebrahimi, T., & Kunt, M. (1998). Video segmentation based on multiple features for 704 interactive multimedia applications. _IEEE Transactions on Circuits and Systems for Video Technology_ , 705 _8_ , 562–571. 

- 706 Chatzis, S. P., & Varvarigou, T. A. (2008). A fuzzy clustering approach toward hidden Markov random field 707 models for enhanced spatially constrained image segmentation. _IEEE Transactions on Fuzzy Systems_ , 708 _16_ , 1351–1361. 

- 709 Chuang, K.-S., Tzeng, H.-L., Chen, S., Wu, J., & Chen, T.-J. (2006). Fuzzy c-means clustering with 710 spatial information for image segmentation. _Computerized medical imaging and graphics_ , _30_ , 9–15. 

- 711 Coppi, R., & D’Urso, P. (2002). Fuzzy _k_ -means clustering models for triangular fuzzy time trajectories. 712 _Statistical Methods and Applications_ , _11_ , 21–40. 

- 713 Coppi, R., & D’Urso, P. (2003). Three-way fuzzy clustering models for LR fuzzy time trajectories. _Com-_ 714 _putational Statistics & Data Analysis_ , _43_ , 149–177. 

- 715 Coppi, R., & D’Urso, P. (2006). Fuzzy unsupervised classification of multivariate time trajectories with 716 the Shannon entropy regularization. _Computational Statistics & Data Analysis_ , _50_ , 1452–1477. 

- 717 Coppi, R., D’Urso, P., & Giordani, P. (2010). A fuzzy clustering model for multivariate spatial time series. 718 _Journal of Classification_ , _27_ , 54–88. 

- 719 Di Nola, A., Loia, V., & Staiano, A. (2000). Genetic-based spatial clustering. In _IEEE International_ 720 _Conference on Fuzzy Systems_ (pp. 953–956). volume 2. 

- 721 Ding, H., Trajcevski, G., Scheuermann, P., Wang, X., & Keogh, E. (2008). Querying and mining of 722 time series data: experimental comparison of representations and distance measures. _Proceedings of the_ 723 _VLDB Endowment_ , _1_ , 1542–1552. 

- 724 Disegna, M., D’Urso, P., & Durante, F. (2017). Copula-based fuzzy clustering of spatial time series. _Spatial_ 725 _Statistics_ , _21_ , 209–225. 

33 

- 726 D’Urso, P. (2000). Dissimilarity measures for time trajectories. _Statistical Methods & Applications_ , _9_ , 727 53–83. 

- 728 D’Urso, P. (2004). Fuzzy C-means clustering models for multivariate time-varying data: Different ap729 proaches. _Internat. J. Uncertain. Fuzziness Knowledge-Based Systems_ , _12_ , 287–326. 

- 730 D’Urso, P. (2005a). Fuzzy clustering for data time arrays with inlier and outlier time trajectories. _IEEE_ 731 _Transactions on Fuzzy Systems_ , _13_ , 583–604. 

- 732 D’Urso, P. (2005b). Fuzzy clustering models for multivariate spatial-time series. In _3rd World Conference_ 733 _on Computational Statistics and Data Analysis_ . 

- 734 D’Urso, P. (2015). Fuzzy clustering. In C. Hennig, M. Meila, F. Murtagh, & R. Rocci (Eds.), _Handbook_ 735 _of Cluster Analysis_ (pp. 545–574). Chapman & Hall. 

- 736 D’Urso, P., Cappelli, C., Di Lallo, D., & Massari, R. (2013a). Clustering of financial time series. _Physica_ 737 _A: Statistical Mechanics and its Applications_ , _392_ , 2114–2129. 

- 738 D’Urso, P., De Giovanni, L., Maharaj, E. A., & Massari, R. (2014). Wavelet-based Self-Organizing Maps 739 for classifying multivariate time series. _Journal of Chemometrics_ , _28_ , 28–51. 

- 740 D’Urso, P., De Giovanni, L., & Massari, R. (2015). Time series clustering by a robust autoregressive metric 741 with application to air pollution. _Chemometrics and Intelligent Laboratory Systems_ , _141(Supplement_ 742 _C)_ , 107–124. 

- 743 D’Urso, P., De Giovanni, L., & Massari, R. (2016). GARCH-based robust clustering of time series. _Fuzzy_ 744 _Sets and Systems_ , _305_ , 1–28. 

- 745 D’Urso, P., De Giovanni, L., & Massari, R. (2018). Robust fuzzy clustering of multivariate time trajectories. 746 _International Journal of Approximate Reasoning_ , _99_ , 12–38. 

- 747 D’Urso, P., Di Lallo, D., & Maharaj, E. A. (2013b). Autoregressive model-based fuzzy clustering and its 748 application for detecting information redundancy in air pollution monitoring networks. _Soft Comput._ , 749 _17_ , 83–131. 

- 750 D’Urso, P., & Maharaj, E. (2009). Autocorrelation-based fuzzy clustering of time series. _Fuzzy Sets and_ 751 _Systems_ , _160_ , 3565–3589. 

- 752 D’Urso, P., & Maharaj, E. A. (2012). Wavelets-based clustering of multivariate time series. _Fuzzy Sets_ 753 _and Systems_ , _193_ , 33–61. 

- 754 D’Urso, P., Maharaj, E. A., & Alonso, A. M. (2017). Fuzzy clustering of time series using extremes. _Fuzzy_ 755 _Sets and Systems_ , _318_ , 56–79. 

- 756 D’Urso, P., Manca, G., Waters, N., & Girone, S. (2019). Visualizing regional clusters of Sardinia’s EU 757 supported agriculture: A Spatial Fuzzy Partitioning Around Medoids. _Land Use Policy_ , _83_ , 571–580. 

- 758 D’Urso, P., Massari, R., Cappelli, C., & De Giovanni, L. (2017). Autoregressive metric-based trimmed 759 fuzzy clustering with an application to _pm_ 10 time series. _Chemometrics and Intelligent Laboratory_ 760 _Systems_ , _13_ , 583–604. 

- 761 Ester, M., Kriegel, H.-P., Sander, J., & Xu, X. (1996). A density-based algorithm for discovering clusters in 762 large spatial databases with noise. In _Proceedings of the Second International Conference on Knowledge_ 763 _Discovery and Data Mining_ KDD’96 (pp. 226–231). AAAI Press. 

34 

- 764 Estivill-Castro, V., & Yang, J. (2004). Fast and robust general purpose clustering algorithms. _Data Mining_ 765 _and Knowledge Discovery_ , _8_ , 127–150. 

- 766 Everitt, B., Landau, S., & Leese, M. (2001). _Cluster Analysis_ . (Forth ed.). London: Arnold Press. 

- 767 Fouedjio, F. (2016). A hierarchical clustering method for multivariate geostatistical data. _Spatial Statistics_ , 768 _18_ , 333–351. 

- 769 Gao, X., & Yu, F. (2016). Fuzzy C-means with spatiotemporal constraints. _Proceedings - 2016 IEEE_ 770 _International Symposium on Computer, Consumer and Control, IS3C 2016_ , (pp. 337–340). 

- 771 Garc´ıa-Escudero, L., & Gordaliza, A. (1999). Robustness properties of _k_ means and trimmed _k_ means. 772 _Journal of the American Statistical Association_ , _94_ , 956–969. 

- 773 Garc´ıa-Escudero, L. A., Gordaliza, A., Matr´an, C., & Mayo-Iscar, A. (2010). A review of robust clustering 774 methods. _Advances in Data Analysis and Classification_ , _4_ , 89–109. 

- 775 Geman, S., & Geman, D. (1987). Stochastic relaxation, Gibbs distributions, and the Bayesian restoration 776 of images. In _Readings in Computer Vision_ (pp. 564–584). Elsevier. 

- 777 Giorgino, T. (2009). Computing and visualizing dynamic time warping alignments in R: the dtw package. 778 _Journal of Statistical Software_ , _31_ , 1–24. 

- 779 Gittleman, J., & Kot, M. (1990). Adaptation: Statistics and a null model for estimating phylogenetic 780 effects. _Systematic Zoology_ , _39_ , 227–241. 

- 781 Gordon, A. D. (1999). _Classification, (Chapman & Hall/CRC Monographs on Statistics & Applied Prob-_ 782 _ability)_ . Chapman and Hall/CRC. 

- 783 Gordon, A. D., & Vichi, M. (2001). Fuzzy partition models for fitting a set of partitions. _Psychometrika_ , 784 _66_ , 229–247. 

- 785 Hamilton, N. E., & Ferry, M. (2018). ggtern: Ternary diagrams using ggplot2. _Journal of Statistical_ 786 _Software, Code Snippets_ , _87_ , 1–17. doi: `10.18637/jss.v087.c03` . 

- 787 Handl, J., Knowles, J., & Kell, D. (2005). Computational cluster validation in post-genomic data analysis. 788 _Bioinformatics_ , _21_ , 3201–3212. 

- 789 Hao, J., Zhao, J., & Li, M. (2010). Spatial continuity incorporated multi-attribute fuzzy clustering algo790 rithm for blood vessels segmentation. _Science China Information Sciences_ , _53_ , 752–759. 

- 791 Hathaway, R. J., & Bezdek, J. C. (1994). NERF c-means: Non-Euclidean relational fuzzy clustering. 792 _Pattern recognition_ , _27_ , 429–437. 

- 793 Hu, T., & Sung, S. (2006). A hybrid EM approach to spatial clustering. _Computational Statistics & Data_ 794 _Analysis_ , _50_ , 1188–1205. 

- 795 H¨ullermeier, E., Rifqi, M., Henzgen, S., & Senge, R. (2012). Comparing Fuzzy Partitions: A Generalization 796 of the Rand Index and Related Measures. _IEEE T. Fuzzy Systems_ , _20_ , 546–556. 

- 797 Hwang, H., DeSarbo, W., & Takane, Y. (2007). Fuzzy clusterwise generalized structured component 798 analysis. _Psychometrika_ , _72_ , 181–198. 

- 799 Ienco, D., & Bordogna, G. (2016). Fuzzy extensions of the DBScan clustering algorithm. _Soft Comput._ , 800 _in press_ , 1–12. 

35 

- 801 Izakian, H., Pedrycz, W., & Jamal, I. (2013). Clustering spatiotemporal data: An augmented fuzzy 802 C-means. _IEEE Transactions of Fuzzy Systems_ , _21_ , 855–868. 

- 803 Izakian, H., Pedrycz, W., & Jamal, I. (2015). Fuzzy clustering of time series data using dynamic time 804 warping distance. _Engineering Applications of Artificial Intelligence_ , _39_ , 235–244. 

- 805 James, G., & Sugar, C. (2003). Clustering for sparsely sampled functional data. _J. Amer. Statist. Assoc._ , 806 _98_ , 397–408. 

- 807 Jeong, Y.-S., Jeong, M., & Omitaomu, O. (2011). Weighted dynamic time warping for time series classifi808 cation. _Pattern Recogn._ , _44_ , 2231–2240. 

- 809 Kalpakis, K., Gada, D., & Puttagunta, V. (2001). Distance measures for effective clustering of ARIMA 810 time-series. _Proceedings - IEEE International Conference on Data Mining, ICDM_ , (pp. 273–280). 

- 811 Kamdar, T., & Joshi, A. (2000). On creating adaptive web servers using weblog mining. In _Technical_ 812 _Report TR-CS-00-05_ (pp. 1–19). Baltimore County: Department of Computer Science and Electrical 813 Engineering, University of Maryland. 

- 814 Kaufman, L., & Rousseeuw, P. (2005). _Finding Groups in Data: An Introduction to Cluster Analysis_ . 815 John Wiley & Sons. 

- 816 Krishnapuram, R., & Freg, C. (1992). Fitting an unknown number of lines and planes to image data 817 through compatible cluster merging. _Pattern Recogn._ , _25_ , 385–400. 

- 818 Krishnapuram, R., Joshi, A., Nasraoui, O., & Yi, L. (2001). Low-complexity fuzzy relational clustering 819 algorithms for web mining. _Fuzzy Systems, IEEE Transactions on_ , _9_ , 595–607. 

- 820 Lafuente-Rego, B., & Vilar, J. (2016). Clustering of time series using quantile autocovariances. _Adv. Data_ 821 _Anal. Classif._ , _10_ , 391–415. 

- 822 Li, X., Zhang, T., & Qu, Z. (2008). Image segmentation using fuzzy clustering with spatial constraints 823 based on markov random field via bayesian theory. _IEICE Transactions on Fundamentals of Electronics,_ 824 _Communications and Computer Sciences_ , _91_ , 723–729. 

- 825 Liew, A., Leung, S., & Lau, W. (2000). Fuzzy image clustering incorporating spatial continuity. _IEE_ 826 _Proceedings-Vision, Image and Signal Processing_ , _147_ , 185–192. 

- 827 Liew, A.-C., Leung, S. H., & Lau, W. H. (2003). Segmentation of color lip images by spatial fuzzy 828 clustering. _IEEE transactions on Fuzzy Systems_ , _11_ , 542–549. 

- 829 Ma, T., Hong, T., & Zhang, H. (2015). Tourism spatial spillover effects and urban economic growth. 830 _Journal of Business Research_ , _68_ , 74–80. 

- 831 Maharaj, E. (1996). A significance test for classifying ARMA models. _J. Stat. Comput. Simul._ , _54_ , 832 305–331. 

- 833 Maharaj, E., & D’Urso, P. (2010). A coherence-based approach for the pattern recognition of time series. 834 _Physica A_ , _389_ , 3516–3537. 

- 835 Maharaj, E., & D’Urso, P. (2011). Fuzzy clustering of time series in the frequency domain. _Inform. Sci._ , 836 _181_ , 1187–1211. 

- 837 Maharaj, E., D’Urso, P., & Galagedera, D. (2010). Wavelet-based Fuzzy Clustering of Time Series. _J._ 838 _Classification_ , _27_ , 231–275. 

36 

- 839 McBratney, A., & Moore, A. (1985). Application of fuzzy sets to climatic classification. _Agricultural and_ 840 _forest meteorology_ , _35_ , 165–185. 

- 841 Mure, S., Grenier, T., Guttmann, C. R., & Benoit-Cattin, H. (2016). Unsupervised time-series clustering 842 of distorted and asynchronous temporal patterns. In _Acoustics, Speech and Signal Processing (ICASSP),_ 843 _2016 IEEE International Conference on_ (pp. 1263–1267). IEEE. 

- 844 Oates, T., Firoiu, L., & Cohen, P. R. (1999). Clustering time series with hidden markov models and 845 dynamic time warping. In _Proceedings of the IJCAI-99 workshop on neural, symbolic and reinforcement_ 846 _learning methods for sequence learning_ (pp. 17–21). Citeseer. 

- 847 Otranto, E. (2010). Identifying financial time series with similar dynamic conditional correlation. _Com-_ 848 _putational Statistics & Data Analysis_ , _54_ , 1–15. 

- 849 P´aez, A., & Scott, D. (2005). Spatial statistics for urban analysis: A review of techniques with examples. 850 _GeoJournal_ , _61_ , 61–53. 

- 851 Petitjean, F., Ketterlin, A., & Gan¸carski, P. (2011). A global averaging method for dynamic time warping, 852 with applications to clustering. _Pattern Recognition_ , _44_ , 678–693. 

- 853 Pham, D. (2001). Spatial models for fuzzy clustering. _Computer Vision and Image Understanding_ , _84_ , 854 285–297. 

- 855 Pham, D. L., & Prince, J. L. (1999). Adaptive fuzzy segmentation of magnetic resonance images. _IEEE_ 856 _transactions on medical imaging_ , _18_ , 737–752. 

- 857 Piccolo, D. (1990). A distance measure for classifying ARIMA models. _J. Time Ser. Anal._ , _11_ , 153–164. 

- 858 Rakthanmanon, T., Campana, B., Mueen, A., Batista, G., Westover, B., Zhu, Q., Zakaria, J., & Keogh, 859 E. (2012). Searching and mining trillions of time series subsequences under dynamic time warping. 860 In _Proceedings of the 18th ACM SIGKDD international conference on Knowledge discovery and data_ 861 _mining_ (pp. 262–270). ACM. 

- 862 Sato, M., & Sato, Y. (1994). On a multicriteria fuzzy clustering method for 3-way data. _International_ 863 _Journal of Uncertainty, Fuzziness and Knowledge-Based Systems_ , _02_ , 127–142. 

- 864 Sato, M., Sato, Y., & Jain, L. (1997). _Fuzzy Clustering Models and Applications_ . Physica-Verlag. 

- 865 Shekhar, S., Jiang, Z., Ali, R., Eftelioglu, E., Tang, X., Gunturi, V., & Zhou, X. (2015). Spatiotemporal 866 data mining: A computational perspective. _ISPRS International Journal of Geo-Information_ , _4_ , 2306– 867 2338. 

- 868 Simbahan, G. C., & Dobermann, A. (2006). An algorithm for spatially constrained classification of cate869 gorical and continuous soil properties. _Geoderma_ , _136_ , 504–523. 

- 870 Subudhi, B. N., Bovolo, F., Ghosh, A., & Bruzzone, L. (2014). Spatio-contextual fuzzy clustering with 871 Markov random field model for change detection in remotely sensed images. _Optics & Laser Technology_ , 872 _57_ , 284–292. 

- 873 Tolias, Y. A., & Panas, S. M. (1998a). Image segmentation by a fuzzy clustering algorithm using adaptive 874 spatially constrained membership functions. _IEEE Transactions on Systems, Man, and Cybernetics-Part_ 875 _A: Systems and Humans_ , _28_ , 359–369. 

- 876 Tolias, Y. A., & Panas, S. M. (1998b). On applying spatial constraints in fuzzy image clustering using a 877 fuzzy rule-based system. _IEEE Signal Processing Letters_ , _5_ , 245–247. 

37 

- 878 Torabi, M. (2014). Spatial generalized linear mixed models with multivariate CAR models for areal data. 879 _Spat. Statist._ , _10_ , 12–26. 

- 880 Torabi, M. (2016). Hierarchical multivariate mixture generalized linear models for the analysis of spatial 881 data: An application to disease mapping. _Biom. J._ , _58_ , 1138–1150. 

- 882 Velichko, V., Sato, M., & Zagoruyko, N. (1970). Automatic recognition of 200 words. _International Journal_ 883 _of Man-Machine Studies_ , _2_ , 223–234. 

- 884 Vilar, J. A., Lafuente-Rego, B., & D’Urso, P. (2017). Quantile autocovariances: a powerful tool for hard 885 and soft partitional clustering of time series. _Fuzzy Sets and Systems_ , (p. in press). 

- 886 Viroli, C. (2011). Finite mixtures of matrix normal distributions for classifying three-way data. _Stat._ 887 _Comput._ , _21_ , 511–522. 

- 888 Wang, M., Wang, A., & Li, A. (2006). Mining spatial-temporal clusters from geo-databases. In X. Li, 889 O. R. Za¨ıane, & Z. Li (Eds.), _Advanced Data Mining and Applications: Second International Conference,_ 890 _ADMA 2006, Xi’an, China, August 14-16, 2006 Proceedings_ Advanced Data Mining and Applications 891 (pp. 263–270). Berlin, Germany: Springer. 

- 892 Wang, Z. M., Soh, Y. C., Song, Q., & Sim, K. (2009). Adaptive spatial information-theoretic clustering 893 for image segmentation. _Pattern Recognition_ , _42_ , 2029–2044. 

- 894 Warren Liao, T. (2005). Clustering of time series data - a survey. _Pattern Recogn._ , _38_ , 1857–1874. 

- 895 Wedel, M., & Kamakura, W. A. (2000). _Market Segmentation: Conceptual and Methodological Founda-_ 896 _tions_ . (2nd ed.). Dordrecht: Kluwer Academic Publishers. 

- 897 Xie, J., Gao, H., Xie, W., Liu, X., & Grant, P. (2016). Robust clustering by detecting density peaks and 898 assigning points based on fuzzy weighted _K_ -nearest neighbors. _Inform. Sci._ , _354_ , 19–40. 

- 899 Xie, X., & Beni, G. (1991). A validity measure for fuzzy clustering. _IEEE Trans. Pattern Anal. Mach._ 900 _Intell._ , _13_ , 841–847. 

- 901 Yang, M.-S., & Tsai, H.-S. (2008). A Gaussian kernel-based fuzzy c-means algorithm with a spatial bias 902 correction. _Pattern recognition letters_ , _29_ , 1713–1725. 

- 903 Yang, Y. (2012). Agglomeration density and tourism development in China: An empirical research based 904 on dynamic panel data model. _Tourism Manage._ , _33_ , 1347–1359. 

- 905 Yang, Y., & Fik, T. (2014). Spatial effects in regional tourism growth. _Annals of Tourism Research_ , _46_ , 906 144–162. 

- 907 Zhang, D. Q., & Chen, S. C. (2004). A novel kernelized fuzzy c-means algorithm with application in 908 medical image segmentation. _Artificial Intelligence in Medicine_ , _32_ , 37–50. 

38 

## 909 **Appendix A. Simulation studies** 

910 _Appendix A.1. Simulation study 1_ 

In this section, we report some further comments on the first simulation study. 

911 In this section, we report some further comments on the first simulation study. 912 The medoids and the fuzzy membership obtained are illustrated in Table A.8. The 913 medoids’ membership degrees are highlighted in bold. As we can observe, the medoids are 914 units 3 and 7 over all the data configurations. Furthermore, in each data configuration 915 the membership degrees of units 4 and 5 to each cluster decrease or increase alternating 916 the greater weight between the contiguity matrices **P** 1 and **P** 2. In data configuration 4), 917 where units 4 and 5 are closest, units 5 is in the same cluster of unit 4 when the weight of 918 **P** 1 is greater than the weight of **P** 2 ( _β_ 1 = 4 and _β_ 2 = 0; _β_ 1 = 8 and _β_ 2 = 0); in different 919 clusters when the weight of **P** 2 is greater than the weight of **P** 1 ( _β_ 1 = 0 and _β_ 2 = 4; _β_ 1 = 0 920 and _β_ 2 = 8). In data configuration 4) when _β_ 1 = 8 and _β_ 2 = 0 the clusters are (medoid 921 in bold) (1, 2, **3** , 4, 5) and (6, **7** , 8); when _β_ 1 = 0 and _β_ 2 = 8 the clusters are (medoid in 922 bold) (1, 2, **3** , 4) and (5, 6, **7** , 8). 

- 923 The performance of the proposed clustering method measured by the Fuzzy Silhouette 924 index _FS_ —is described in Table A.9. As it can be seen, going from configuration 1) to 4) 925 the value of the silhouette increases. In fact the medoids remain the same (3 and 7) and 926 the _fuzzy_ units 4 and 5 decrease their membership to the natural clusters (1, 2, 3) and 927 (7, 8, 9). 

## 928 _Appendix A.2. Simulation study 2_ 

- 929 In this section, we report some further comments on the second simulation study. 930 The medoids and the fuzzy membership are illustrated in Tables A.10 and A.11. As 931 we can observe, the medoids are units 3, 7, 9, 14 over the data configurations 1) and 2); 932 units 4, 5, 12, 13 over almost all the data configurations 3) and 4). Table A.10 and A.11 933 show that in each data configuration the membership degrees of units 4, 5, 12, 13 to each 934 cluster decrease or increase alternating the greater weight between **P** 1 and **P** 2. In data 935 configuration 3), where units 4, 5, 12, 13 are getting closer: 1) when _β_ 1 = 20 and _β_ 2 = 0 936 the units 4, 5, 12, 13 are in the same cluster and the clusters are (medoid in bold): (1, 2, 937 **3** ), (6, **7** , 8), (4, 5, 9, 10, 11, **12** , 13), ( **14** , 15, 16); 2) when _β_ 1 = 0 and _β_ 2 = 20 the units 938 4, 5, 12, 13 are in different clusters and the clusters are (medoid in bold) (1, 2, **3** , 4), (5, 939 6, **7** , 8), ( **9** , 10, 11,12), (13, **14** , 15, 16). 

- 940 In Table A.12 the main conclusions of the simulation study are reported. Notice that, 941 going from configuration 1), 2) to 3), 4), the value of the silhouette decreases. In configu942 rations 1), 2) the medoids are 3, 7, 9, 14; in configurations 3), 4) the medoids are almost 943 always 4, 5, 12, 13 (the _fuzzy_ units). The performances get worse in data configuration 944 3) and 4) in relation to the increased similarity of the fuzzy units 4, 5, 12, 13. The best 945 performance in data configuration 3) is ( _β_ 1, _β_ 2)= (20, 0) where the medoids are 3, 7, 12, 946 14 and the high weight of **P** 1 constraints the four fuzzy units in the same cluster (medoid 947 12). 

39 

|(_β_1_, β_2)|(0_,_|0)|(4_,_|0)|(0_,_|4)|(8_,_|0)|(0|_,_ 8)|
|---|---|---|---|---|---|---|---|---|---|---|
|||||**D**|**ata confi**|**iguration **|**1)**||||
|cluster|1|2|1|2|1|2|1|2|1|2|
|1|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|
|2|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|
|3|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|
|4|0.7907|0.2093|0.8086|0.1914|0.8160|0.1840|0.8235|0.1765|0.8372|0.1628|
|5|0.3311|0.6689|0.3305|0.6695|0.2934|0.7066|0.3308|0.6692|0.2611|0.7389|
|6|0.0000|1.0000|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|
|7|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|
|8|0.0003|0.9997|0.0003|0.9997|0.0003|0.9997|0.0003|0.9997|0.0003|0.9997|
|||||**D**|**ata confi**|**iguration **|**2)**||||
|cluster|1|2|1|2|1|2|1|2|1|2|
|1|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|
|2|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|
|3|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|
|4|0.7407|0.2593|0.7654|0.2346|0.7715|0.2285|0.7860|0.2140|0.7976|0.2024|
|5|0.3889|0.6111|0.3848|0.6152|0.3457|0.6543|0.3824|0.6176|0.3083|0.6917|
|6|0.0000|1.0000|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|
|7|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|
|8|00003|09997|00003|09997|00003|09997|00003|09997|00004|09996|
||.|.|.|.<br>**D**|.<br>**ata confi**|.<br>**iguration **|.<br> **3)**|.|.|.|
|cluster|1|2|1|2|1|2|1|2|1|2|
|1|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|
|2|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|
|3|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|
|4|0.6844|0.3156|0.7654|0.2346|0.7715|0.2285|0.7860|0.2140|0.7976|0.2024|
|5|0.4500|0.5500|0.3848|0.6152|0.3457|0.6543|0.3824|0.6176|0.3083|0.6917|
|6|0.0000|1.0000|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|
|7|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|
|8|0.0003|0.9997|0.0003|0.9997|0.0003|0.9997|0.0003|0.9997|0.0004|0.9996|
|||||**D**|**ata confi**|**iguration **|**4)**||||
|cluster|1|2|1|2|1|2|1|2|1|2|
|1|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|
|2|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|0.9999|0.0001|
|3|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|
|4|0.6271|0.3729|0.6853|0.3147|0.6689|0.3311|0.7168|0.2832|0.7051|0.2949|
|5|0.4874|0.5126|0.5256|0.4744|0.4603|0.5397|0.5169|0.4831|0.4138|0.5862|
|6|0.0000|1.0000|0.0000|1.0000|0.0001|0.9999|0.0000|1.0000|0.0001|0.9999|
|7|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|**0.0000**|**1.0000**|
|8|0.0003|0.9997|0.0001|0.9999|0.0004|0.9996|0.0001|0.9999|0.0004|0.9996|



Note: Medoids’ membership degrees are in bold. 

Table A.8: Membership degrees for simulation study 1, according to different combinations of _β_ 1 and _β_ 2 and data configurations 

40 

|**Data**||(_β_1_,_|_β_2)|||
|---|---|---|---|---|---|
|**configuration**|(0, 0)|(4, 0)|(0, 4)|(8, 0)|0, 8|
|1)|0.82|0.82|0.81|0.81|0.80|
|2)|0.82|0.82|0.81|0.81|0.80|
|3)|0.84|0.82|0.81|0.81|0.80|
|4)|0.90|0.89|0.83|0.89|0.80|



Table A.9: Fuzzy Silhouette index values for simulation study 1 according to different setting of the parameters _β_ 1 _, β_ 2 (column wise) and to data configuration (row wise) 

41 

|(0_,_ 20)<br>1<br>2<br>3<br>4<br>0.9992<br>0.0003<br>0.0001<br>0.0003<br>0.9993<br>0.0003<br>0.0001<br>0.0003<br>**1.0000 0.0000 0.0000 0.0000**<br>0.9628<br>0.0154<br>0.0055<br>0.0163<br>0.0130<br>0.9705<br>0.0106<br>0.0059<br>0.0001<br>0.9998<br>0.0001<br>0.0000<br>**0.0000 1.0000 0.0000 0.0000**<br>0.0007<br>0.9985<br>0.0006<br>0.0002<br>**0.0000 0.0000 1.0000 0.0000**<br>0.0001<br>0.0003<br>0.9993<br>0.0003<br>0.0000<br>0.0001<br>0.9998<br>0.0001<br>0.0076<br>0.0199<br>0.9511<br>0.0215<br>0.0071<br>0.0027<br>0.0067<br>0.9835<br>**0.0000 0.0000 0.0000 1.0000**<br>0.0001<br>0.0000<br>0.0001<br>0.9997<br>0.0001<br>0.0000<br>0.0001<br>0.9998<br>1<br>2<br>3<br>4<br>0.9991<br>0.0004<br>0.0001<br>0.0004<br>0.9992<br>0.0004<br>0.0001<br>0.0004<br>**1.0000 0.0000 0.0000 0.0000**<br>0.8781<br>0.0487<br>0.0207<br>0.0525<br>0.0438<br>0.8965<br>0.0357<br>0.0240<br>0.0001<br>0.9997<br>0.0001<br>0.0000<br>**0.0000 1.0000 0.0000 0.0000**<br>0.0007<br>0.9984<br>0.0007<br>0.0002<br>**0.0000 0.0000 1.0000 0.0000**<br>0.0001<br>0.0004<br>0.9991<br>0.0004<br>0.0000<br>0.0001<br>0.9997<br>0.0002<br>0.0260<br>0.0586<br>0.8526<br>0.0628<br>0.0285<br>0.0135<br>0.0268<br>0.9312<br>**0.0000 0.0000 0.0000 1.0000**<br>0.0001<br>0.0000<br>0.0001<br>0.9997<br>0.0001<br>0.0000<br>0.0001<br>0.9997|2)|
|---|---|
|4<br>0.0005<br>0.0005<br> **0.0000**<br>0.0869<br>0.0384<br>0.0001<br> **0.0000**<br>0.0003<br> **0.0000**<br>0.0005<br>0.0002<br>0.0949<br>0.8416<br> **1.0000**<br>0.9995<br>0.9996<br>4<br>0.0007<br>0.0006<br> **0.0000**<br>0.1252<br>0.0655<br>0.0001<br> **0.0000**<br>0.0003<br> **0.0000**<br>0.0006<br>0.0004<br>0.1354<br>0.7733<br> **1.0000**<br>0.9994<br>0.9995|) and|
|(20_,_ 0)<br>2<br>3<br>0.0005<br>0.0001<br>0.0005<br>0.0001<br> **0.0000 0.0000**<br>0.0821<br>0.0329<br>0.8228<br>0.0630<br>0.9996<br>0.0002<br> **1.0000 0.0000**<br>0.9981<br>0.0008<br> **0.0000 1.0000**<br>0.0005<br>0.9989<br>0.0001<br>0.9996<br>0.0885<br>0.7790<br>0.0290<br>0.0631<br> **0.0000 0.0000**<br>0.0001<br>0.0002<br>0.0000<br>0.0002<br>2<br>3<br>0.0007<br>0.0002<br>0.0006<br>0.0002<br> **0.0000 0.0000**<br>0.1160<br>0.0541<br>0.7357<br>0.0903<br>0.9995<br>0.0002<br> **1.0000 0.0000**<br>0.9978<br>0.0009<br> **0.0000 1.0000**<br>0.0006<br>0.9985<br>0.0002<br>0.9993<br>0.1260<br>0.6771<br>0.0481<br>0.0866<br> **0.0000 0.0000**<br>0.0001<br>0.0003<br>0.0001<br>0.0002|irations 1|
|1<br>0.9989<br>0.9990<br>**1.0000 **<br>0.7981<br>0.0758<br>0.0002<br>**0.0000 **<br>0.0008<br>**0.0000 **<br>0.0001<br>0.0000<br>0.0376<br>0.0663<br>**0.0000 **<br>0.0002<br>0.0001<br>1<br>0.9985<br>0.9987<br>**1.0000 **<br>0.7047<br>0.1085<br>0.0002<br>**0.0000 **<br>0.0010<br>**0.0000 **<br>0.0002<br>0.0001<br>0.0615<br>0.0920<br>**0.0000 **<br>0.0003<br>0.0002|nfigu|
|4<br>0.0004<br>0.0003<br> **0.0000**<br>0.0186<br>0.0064<br>0.0000<br> **0.0000**<br>0.0002<br> **0.0000**<br>0.0003<br>0.0001<br>0.0245<br>0.9813<br> **1.0000**<br>0.9997<br>0.9998<br>4<br>0.0004<br>0.0004<br> **0.0000**<br>0.0599<br>0.0263<br>0.0000<br> **0.0000**<br>0.0002<br> **0.0000**<br>0.0004<br>0.0002<br>0.0715<br>0.9221<br> **1.0000**<br>0.9996<br>0.9997|ta coi|
|16)<br>3<br>0.0001<br>0.0001<br> **0.0000 **<br>0.0059<br>0.0118<br>0.0001<br> **0.0000 **<br>0.0007<br> **1.0000 **<br>0.9993<br>0.9998<br>0.9448<br>0.0076<br> **0.0000 **<br>0.0001<br>0.0001<br>3<br>0.0001<br>0.0001<br> **0.0000 **<br>0.0223<br>0.0399<br>0.0001<br> **0.0000 **<br>0.0007<br> **1.0000 **<br>0.9991<br>0.9997<br>0.8343<br>0.0306<br> **0.0000 **<br>0.0002<br>0.0001|to da|
|(0_,_<br>2<br>0.0004<br>0.0003<br> **0.0000 **<br>0.0175<br>0.9670<br>0.9997<br> **1.0000 **<br>0.9984<br> **0.0000 **<br>0.0003<br>0.0001<br>0.0226<br>0.0030<br> **0.0000 **<br>0.0000<br>0.0000<br>2<br>0.0005<br>0.0004<br> **0.0000 **<br>0.0553<br>0.8842<br>0.9997<br> **1.0000 **<br>0.9983<br> **0.0000 **<br>0.0004<br>0.0001<br>0.0663<br>0.0147<br> **0.0000 **<br>0.0000<br>0.0000|and|
|1<br>0.9992<br>0.9992<br>**1.0000**<br>0.9579<br>0.0148<br>0.0001<br>**0.0000**<br>0.0007<br>**0.0000**<br>0.0001<br>0.0000<br>0.0081<br>0.0081<br>**0.0000**<br>0.0001<br>0.0001<br>1<br>0.9990<br>0.9991<br>**1.0000**<br>0.8625<br>0.0497<br>0.0001<br>**0.0000**<br>0.0008<br>**0.0000**<br>0.0001<br>0.0000<br>0.0280<br>0.0326<br>**0.0000**<br>0.0002<br>0.0001|_β_2,|
|4<br>0.0005<br>0.0004<br> **0.0000**<br><br>0.0816<br>0.0338<br>0.0001<br> **0.0000**<br><br>0.0003<br> **0.0000**<br><br>0.0005<br>0.0002<br>0.0902<br>0.8583<br> **1.0000**<br><br>0.9996<br>0.9997<br>4<br>0.0006<br>0.0006<br> **0.0000**<br><br>0.1245<br>0.0618<br>0.0001<br> **0.0000**<br><br>0.0003<br> **0.0000**<br><br>0.0006<br>0.0003<br>0.1358<br>0.7839<br> **1.0000**<br><br>0.9994<br>0.9995|1 and|
|(16_,_ 0)<br>**iuration 1)**<br>1<br>2<br>3<br>0.9989<br>0.0005<br>0.0001<br>0.9990<br>0.0004<br>0.0001<br>**1.0000 0.0000 0.0000**<br>0.8128<br>0.0767<br>0.0289<br>0.0703<br>0.8384<br>0.0575<br>0.0001<br>0.9996<br>0.0002<br>**0.0000 1.0000 0.0000**<br>0.0008<br>0.9981<br>0.0008<br>**0.0000 0.0000 1.0000**<br>0.0001<br>0.0004<br>0.9990<br>0.0000<br>0.0001<br>0.9996<br>0.0334<br>0.0836<br>0.7928<br>0.0601<br>0.0247<br>0.0569<br>**0.0000 0.0000 0.0000**<br>0.0002<br>0.0001<br>0.0002<br>0.0001<br>0.0000<br>0.0002<br>**iuration 2)**<br>1<br>2<br>3<br>0.9986<br>0.0007<br>0.0001<br>0.9987<br>0.0006<br>0.0001<br>**1.0000 0.0000 0.0000**<br>0.7102<br>0.1148<br>0.0505<br>0.1069<br>0.7438<br>0.0876<br>0.0002<br>0.9995<br>0.0002<br>**0.0000 1.0000 0.0000**<br>0.0010<br>0.9978<br>0.0009<br>**0.0000 0.0000 1.0000**<br>0.0002<br>0.0006<br>0.9986<br>0.0001<br>0.0002<br>0.9994<br>0.0579<br>0.1257<br>0.6807<br>0.0889<br>0.0440<br>0.0833<br>**0.0000 0.0000 0.0000**<br>0.0002<br>0.0001<br>0.0002<br>0.0002<br>0.0001<br>0.0002|binations of_β_|
|(0_,_ 12)<br>**Data config**<br>4<br>1<br>2<br>3<br>4<br>0.0005<br>0.9991<br>0.0004<br>0.0001<br>0.0004<br>0.0004<br>0.9992<br>0.0004<br>0.0001<br>0.0004<br>**0.0000**<br>**1.000**0 **0.0000 0.0000 0.0000**<br><br>0.0746<br>0.9521<br>0.0200<br>0.0064<br>0.0215<br>0.0287<br>0.0169<br>0.9628<br>0.0133<br>0.0070<br>0.0000<br>0.0001<br>0.9997<br>0.0001<br>0.0000<br>**0.0000**<br>**0.0000 1.0000 0.0000 0.0000**<br><br>0.0002<br>0.0008<br>0.9983<br>0.0007<br>0.0002<br>**0.0000**<br>**0.0000 0.0000 1.0000 0.0000**<br><br>0.0004<br>0.0001<br>0.0003<br>0.9992<br>0.0004<br>0.0002<br>0.0000<br>0.0001<br>0.9998<br>0.0001<br>0.0839<br>0.0088<br>0.0258<br>0.9372<br>0.0282<br>0.8783<br>0.0093<br>0.0032<br>0.0088<br>0.9787<br>**1.0000**<br>**0.0000 0.0000 0.0000 1.0000**<br><br>0.9996<br>0.0002<br>0.0000<br>0.0002<br>0.9997<br>0.9997<br>0.0001<br>0.0000<br>0.0001<br>0.9997<br>**Data config**<br>4<br>1<br>2<br>3<br>4<br>0.0006<br>0.9989<br>0.0005<br>0.0001<br>0.0005<br>0.0005<br>0.9990<br>0.0004<br>0.0001<br>0.0004<br>**0.0000**<br>**1.000**0 **0.0000 0.0000 0.0000**<br><br>0.1234<br>0.8437<br>0.0632<br>0.0241<br>0.0690<br>0.0574<br>0.0568<br>0.8695<br>0.0449<br>0.0288<br>0.0001<br>0.0001<br>0.9997<br>0.0001<br>0.0000<br>**0.0000**<br>**0.0000 1.0000 0.0000 0.0000**<br><br>0.0003<br>0.0008<br>0.9981<br>0.0008<br>0.0002<br>**0.0000**<br>**0.0000 0.0000 1.0000 0.0000**<br><br>0.0006<br>0.0001<br>0.0004<br>0.9990<br>0.0004<br>0.0003<br>0.0000<br>0.0001<br>0.9997<br>0.0002<br>0.1358<br>0.0301<br>0.0755<br>0.8125<br>0.0819<br>0.7967<br>0.0377<br>0.0161<br>0.0351<br>0.9111<br>**1.0000**<br>**0.0000 0.0000 0.0000 1.0000**<br><br>0.9995<br>0.0002<br>0.0000<br>0.0002<br>0.9996<br>0.9996<br>0.0001<br>0.0000<br>0.0001<br>0.9997|cording to different com|
|0)<br>3<br>0.0001<br>0.0001<br>**0.0000 **<br>0.0244<br>0.0509<br>0.0002<br>**0.0000 **<br>0.0008<br>**1.0000 **<br>0.9990<br>0.9997<br>0.8100<br>0.0494<br>**0.0000 **<br>0.0002<br>0.0002<br>3<br>0.0001<br>0.0001<br>**0.0000 **<br>0.0464<br>0.0842<br>0.0002<br>**0.0000 **<br>0.0009<br>**1.0000 **<br>0.9987<br>0.9995<br>0.6853<br>0.0791<br>**0.0000 **<br>0.0002<br>0.0002|2, ac|
|(12_,_ <br>1<br>2<br>0.9989<br>0.0005<br>0.9990<br>0.0004<br>**1.0000 0.0000 **<br>0.8311<br>0.0698<br>0.0633<br>0.8571<br>0.0001<br>0.9997<br>**0.0000 1.0000 **<br>0.0009<br>0.9981<br>**0.0000 0.0000 **<br>0.0001<br>0.0004<br>0.0000<br>0.0001<br>0.0288<br>0.0773<br>0.0523<br>0.0200<br>**0.0000 0.0000 **<br>0.0002<br>0.0000<br>0.0001<br>0.0000<br>1<br>2<br>0.9986<br>0.0006<br>0.9988<br>0.0005<br>**1.0000 0.0000 **<br>0.7172<br>0.1130<br>0.1047<br>0.7537<br>0.0002<br>0.9996<br>**0.0000 1.0000 **<br>0.0010<br>0.9978<br>**0.0000 0.0000 **<br>0.0002<br>0.0006<br>0.0001<br>0.0002<br>0.0539<br>0.1250<br>0.0849<br>0.0394<br>**0.0000 0.0000 **<br>0.0002<br>0.0001<br>0.0002<br>0.0000|on study|
|(0_,_ 8)<br>1<br>2<br>3<br>4<br>0.9990<br>0.0005<br>0.0001<br>0.0004<br>0.9991<br>0.0004<br>0.0001<br>0.0004<br>**1.0000 0.0000 0.0000 0.0000**<br><br>0.9448<br>0.0232<br>0.0069<br>0.0250<br>0.0195<br>0.9577<br>0.0151<br>0.0077<br>0.0001<br>0.9997<br>0.0001<br>0.0000<br>**0.0000 1.0000 0.0000 0.0000**<br><br>0.0008<br>0.9981<br>0.0008<br>0.0002<br>**0.0000 0.0000 1.0000 0.0000**<br><br>0.0001<br>0.0004<br>0.9991<br>0.0004<br>0.0000<br>0.0001<br>0.9998<br>0.0001<br>0.0095<br>0.0298<br>0.9279<br>0.0328<br>0.0108<br>0.0035<br>0.0101<br>0.9755<br>**0.0000 0.0000 0.0000 1.0000**<br><br>0.0002<br>0.0000<br>0.0002<br>0.9996<br>0.0001<br>0.0000<br>0.0001<br>0.9997<br>1<br>2<br>3<br>4<br>0.9989<br>0.0005<br>0.0001<br>0.0005<br>0.9990<br>0.0005<br>0.0001<br>0.0005<br>**1.0000 0.0000 0.0000 0.0000**<br><br>0.8210<br>0.0729<br>0.0260<br>0.0801<br>0.0656<br>0.8520<br>0.0508<br>0.0316<br>0.0001<br>0.9997<br>0.0002<br>0.0000<br>**0.0000 1.0000 0.0000 0.0000**<br><br>0.0009<br>0.9980<br>0.0008<br>0.0003<br>**0.0000 0.0000 1.0000 0.0000**<br><br>0.0001<br>0.0004<br>0.9990<br>0.0005<br>0.0000<br>0.0001<br>0.9997<br>0.0002<br>0.0324<br>0.0866<br>0.7863<br>0.0947<br>0.0439<br>0.0177<br>0.0407<br>0.8977<br>**0.0000 0.0000 0.0000 1.0000**<br><br>0.0002<br>0.0000<br>0.0002<br>0.9996<br>0.0001<br>0.0000<br>0.0002<br>0.9997<br>.|degrees for simulati|
|)<br>(8_,_ 0)<br>1<br>2<br>3<br>4<br>0.9989<br>0.0005<br>0.0001<br>0.0005<br>0.9990<br>0.0004<br>0.0001<br>0.0004<br>**1.0000 0.0000 0.0000 0.0000**<br><br>0.8544<br>0.0608<br>0.0195<br>0.0654<br>0.0543<br>0.8801<br>0.0428<br>0.0229<br>0.0001<br>0.9997<br>0.0001<br>0.0000<br>**0.0000 1.0000 0.0000 0.0000**<br><br>0.0009<br>0.9980<br>0.0008<br>0.0002<br>**0.0000 0.0000 1.0000 0.0000**<br><br>0.0001<br>0.0004<br>0.9990<br>0.0004<br>0.0000<br>0.0001<br>0.9997<br>0.0002<br>0.0235<br>0.0689<br>0.8323<br>0.0753<br>0.0425<br>0.0149<br>0.0400<br>0.9026<br>**0.0000 0.0000 0.0000 1.0000**<br><br>0.0002<br>0.0000<br>0.0002<br>0.9996<br>0.0001<br>0.0000<br>0.0002<br>0.9997<br>1<br>2<br>3<br>4<br>0.9987<br>0.0006<br>0.0001<br>0.0006<br>0.9989<br>0.0005<br>0.0001<br>0.0005<br>**1.0000 0.0000 0.0000 0.0000**<br><br>0.7265<br>0.1104<br>0.0417<br>0.1214<br>0.1016<br>0.7662<br>0.0800<br>0.0522<br>0.0002<br>0.9996<br>0.0002<br>0.0001<br>**0.0000 1.0000 0.0000 0.0000**<br><br>0.0010<br>0.9978<br>0.0009<br>0.0003<br>**0.0000 0.0000 1.0000 0.0000**<br><br>0.0001<br>0.0005<br>0.9988<br>0.0005<br>0.0000<br>0.0001<br>0.9996<br>0.0002<br>0.0492<br>0.1237<br>0.6918<br>0.1353<br>0.0796<br>0.0342<br>0.0737<br>0.8125<br>**0.0000 0.0000 0.0000 1.0000**<br><br>0.0002<br>0.0001<br>0.0002<br>0.9995<br>0.0001<br>0.0000<br>0.0002<br>0.9996<br>Medoids’ membership degrees are in bold|A.10: Membership|
|(_β_1_, β_2<br>cluster<br>1<br>2<br>3<br>4<br>5<br>6<br>7<br>8<br>9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>cluster<br>1<br>2<br>3<br>4<br>5<br>6<br>7<br>8<br>9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>Note:|Table|



42 

|(0_,_20)|1<br>2<br>3<br>4<br>0.9986<br>0.0006<br>0.0002<br>0.0006<br>0.9987<br>0.0006<br>0.0001<br>0.0006<br>1.0000<br>0.0000<br>0.0000<br>0.0000<br>0.7216<br>0.1059<br>0.0571<br>0.1154<br>0.0988<br>0.7493<br>0.0821<br>0.0697<br>0.0002<br>0.9995<br>0.0002<br>0.0001<br>0.0000<br>1.0000<br>0.0000<br>0.0000<br>0.0010<br>0.9979<br>0.0009<br>0.0003<br>**0.0000 0.0000 1.0000 0.0000**<br>0.0002<br>0.0006<br>0.9986<br>0.0006<br>0.0001<br>0.0002<br>0.9994<br>0.0003<br>0.0669<br>0.1211<br>0.6831<br>0.1289<br>0.0731<br>0.0451<br>0.0682<br>0.8135<br>**0.0000 0.0000 0.0000 1.0000**<br>0.0002<br>0.0001<br>0.0002<br>0.9995<br>0.0002<br>0.0001<br>0.0002<br>0.9996<br>1<br>2<br>3<br>4<br>0.3938<br>0.2240<br>0.1723<br>0.2099<br>0.3750<br>0.2225<br>0.1783<br>0.2243<br>0.4081<br>0.2158<br>0.1650<br>0.2111<br>**1.0000 0.0000 0.0000 0.0000**<br>**0.0000 1.0000 0.0000 0.0000**<br>0.2209<br>0.3656<br>0.2387<br>0.1749<br>0.2127<br>0.3951<br>0.2251<br>0.1670<br>0.2215<br>0.3828<br>0.2207<br>0.1750<br>0.1746<br>0.1969<br>0.4123<br>0.2162<br>0.1768<br>0.2022<br>0.4099<br>0.2111<br>0.1800<br>0.1995<br>0.4003<br>0.2202<br>**0.0000 0.0000 1.0000 0.0000**<br>**0.0000 0.0000 0.0000 1.0000**<br>0.1936<br>0.1547<br>0.1937<br>0.4580<br>0.2038<br>0.1728<br>0.1897<br>0.4338<br>0.2030<br>0.1647<br>0.2063<br>0.4259|
|---|---|
||4<br>0.0023<br>0.0021<br>0.0000<br>0.0980<br>0.0599<br>0.0005<br>0.0000<br>0.0010<br>0.0771<br>0.0600<br>0.0835<br> **0.0000**<br>0.3687<br> **1.0000**<br>0.9933<br>0.9942<br>4<br>0.2099<br>0.2243<br>0.2111<br> **0.0000**<br> **0.0000**<br>0.1749<br>0.1670<br>0.1750<br>0.2162<br>0.2111<br>0.2202<br> **0.0000**<br> **1.0000**<br>0.4580<br>0.4338<br>0.4259|
|(20_,_ 0)|1<br>2<br>3<br>0.9919<br>0.0024<br>0.0034<br>0.9932<br>0.0020<br>0.0027<br>1.0000<br>0.0000<br>0.0000<br>0.3319<br>0.0905<br>0.4797<br>0.0792<br>0.3131<br>0.5479<br>0.0015<br>0.9934<br>0.0046<br>0.0000<br>1.0000<br>0.0000<br>0.0032<br>0.9874<br>0.0084<br>0.0177<br>0.0482<br>0.8570<br>0.0172<br>0.0589<br>0.8640<br>0.0180<br>0.0519<br>0.8466<br>**0.0000 0.0000 1.0000 **<br>0.0756<br>0.0506<br>0.5051<br>**0.0000 0.0000 0.0000 **<br>0.0017<br>0.0005<br>0.0045<br>0.0014<br>0.0004<br>0.0040<br>1<br>2<br>3<br>0.3938<br>0.2240<br>0.1723<br>0.3750<br>0.2225<br>0.1783<br>0.4081<br>0.2158<br>0.1650<br>**1.0000 0.0000 0.0000 **<br>**0.0000 1.0000 0.0000 **<br>0.2209<br>0.3656<br>0.2387<br>0.2127<br>0.3951<br>0.2251<br>0.2215<br>0.3828<br>0.2207<br>0.1746<br>0.1969<br>0.4123<br>0.1768<br>0.2022<br>0.4099<br>0.1800<br>0.1995<br>0.4003<br>**0.0000 0.0000 1.0000 **<br>**0.0000 0.0000 0.0000 **<br>0.1936<br>0.1547<br>0.1937<br>0.2038<br>0.1728<br>0.1897<br>0.2030<br>0.1647<br>0.2063|
||4<br>0.1471<br>0.1762<br>0.1494<br> **0.0000**<br> **0.0000**<br>0.0946<br>0.0801<br>0.0922<br>0.1554<br>0.1451<br>0.1640<br> **0.0000**<br> **1.0000**<br>0.7021<br>0.6639<br>0.6431<br>4<br>0.2155<br>0.2299<br>0.2178<br> **0.0000**<br> **0.0000**<br>0.1775<br>0.1702<br>0.1779<br>0.2233<br>0.2176<br>0.2270<br> **0.0000**<br> **1.0000**<br>0.4372<br>0.4144<br>0.4079|
|(0_,_ 16)|2<br>3<br>0.1665<br>0.0875<br>0.1708<br>0.0971<br>0.1440<br>0.0789<br> **0.0000 0.0000 **<br> **1.0000 0.0000 **<br>0.5555<br>0.1828<br>0.6177<br>0.1535<br>0.5674<br>0.1707<br>0.1303<br>0.6297<br>0.1426<br>0.6262<br>0.1369<br>0.6089<br> **0.0000 1.0000 **<br> **0.0000 0.0000 **<br>0.0647<br>0.1167<br>0.0791<br>0.1224<br>0.0791<br>0.1437<br>2<br>3<br>0.2308<br>0.1756<br>0.2279<br>0.1812<br>0.2228<br>0.1683<br> **0.0000 0.0000 **<br> **1.0000 0.0000 **<br>0.3513<br>0.2451<br>0.3780<br>0.2326<br>0.3688<br>0.2262<br>0.2026<br>0.3955<br>0.2082<br>0.3933<br>0.2048<br>0.3841<br> **0.0000 1.0000 **<br> **0.0000 0.0000 **<br>0.1592<br>0.2019<br>0.1780<br>0.1961<br>0.1687<br>0.2136|
||1<br>0.5990<br>0.5560<br>0.6277<br>**1.0000 **<br>**0.0000 **<br>0.1671<br>0.1486<br>0.1697<br>0.0845<br>0.0862<br>0.0902<br>**0.0000 **<br>**0.0000 **<br>0.1165<br>0.1347<br>0.1341<br>1<br>0.3781<br>0.3610<br>0.3912<br>**1.0000 **<br>**0.0000 **<br>0.2261<br>0.2192<br>0.2271<br>0.1786<br>0.1809<br>0.1841<br>**0.0000 **<br>**0.0000 **<br>0.2017<br>0.2115<br>0.2099|
|(0_,_ 12)<br>(16_,_ 0)<br>**Data configuration 3)**|1<br>2<br>3<br>4<br>1<br>2<br>3<br>4<br>0.5778<br>0.1770<br>0.0900<br>0.1552<br>0.5990<br>0.1665<br>0.0875<br>0.1471<br>0.5358<br>0.1793<br>0.0995<br>0.1854<br>0.5560<br>0.1708<br>0.0971<br>0.1762<br>0.6061<br>0.1532<br>0.0813<br>0.1593<br>0.6277<br>0.1440<br>0.0789<br>0.1494<br>**1.0000 0.0000 0.0000 0.0000**<br>**1.0000 0.0000 0.0000 0.0000**<br>**0.0000 1.0000 0.0000 0.0000**<br>**0.0000 1.0000 0.0000 0.0000**<br>0.1753<br>0.5352<br>0.1927<br>0.0968<br>0.1671<br>0.5555<br>0.1828<br>0.0946<br>0.1581<br>0.5958<br>0.1636<br>0.0825<br>0.1486<br>0.6177<br>0.1535<br>0.0801<br>0.1786<br>0.5473<br>0.1796<br>0.0944<br>0.1697<br>0.5674<br>0.1707<br>0.0922<br>0.0876<br>0.1382<br>0.6076<br>0.1666<br>0.0845<br>0.1303<br>0.6297<br>0.1554<br>0.0894<br>0.1518<br>0.6043<br>0.1545<br>0.0862<br>0.1426<br>0.6262<br>0.1451<br>0.0934<br>0.1447<br>0.5868<br>0.1752<br>0.0902<br>0.1369<br>0.6089<br>0.1640<br>**0.0000 0.0000 1.0000 0.0000**<br>**0.0000 0.0000 1.0000 0.0000**<br>**0.0000 0.0000 0.0000 1.0000**<br>**0.0000 0.0000 0.0000 1.0000**<br>0.1271<br>0.0680<br>0.1274<br>0.6774<br>0.1165<br>0.0647<br>0.1167<br>0.7021<br>0.1459<br>0.0830<br>0.1317<br>0.6394<br>0.1347<br>0.0791<br>0.1224<br>0.6639<br>0.1437<br>0.0824<br>0.1547<br>0.6191<br>0.1341<br>0.0791<br>0.1437<br>0.6431<br>**Data configuration 3)**<br>1<br>2<br>3<br>4<br>1<br>2<br>3<br>4<br>0.3627<br>0.2375<br>0.1787<br>0.2210<br>0.3781<br>0.2308<br>0.1756<br>0.2155<br>0.3475<br>0.2331<br>0.1840<br>0.2354<br>0.3610<br>0.2279<br>0.1812<br>0.2299<br>0.3745<br>0.2298<br>0.1714<br>0.2244<br>0.3912<br>0.2228<br>0.1683<br>0.2178<br>**1.0000 0.0000 0.0000 0.0000**<br>**1.0000 0.0000 0.0000 0.0000**<br>**0.0000 1.0000 0.0000 0.0000**<br>**0.0000 1.0000 0.0000 0.0000**<br>0.2312<br>0.3375<br>0.2515<br>0.1799<br>0.2261<br>0.3513<br>0.2451<br>0.1775<br>0.2256<br>0.3610<br>0.2401<br>0.1732<br>0.2192<br>0.3780<br>0.2326<br>0.1702<br>0.2327<br>0.3552<br>0.2315<br>0.1807<br>0.2271<br>0.3688<br>0.2262<br>0.1779<br>0.1825<br>0.2081<br>0.3790<br>0.2304<br>0.1786<br>0.2026<br>0.3955<br>0.2233<br>0.1848<br>0.2141<br>0.3771<br>0.2240<br>0.1809<br>0.2082<br>0.3933<br>0.2176<br>0.1879<br>0.2100<br>0.3683<br>0.2338<br>0.1841<br>0.2048<br>0.3841<br>0.2270<br>**0.0000 0.0000 1.0000 0.0000**<br>**0.0000 0.0000 1.0000 0.0000**<br>**0.0000 0.0000 0.0000 1.0000**<br>**0.0000 0.0000 0.0000 1.0000**<br>0.2097<br>0.1635<br>0.2100<br>0.4168<br>0.2017<br>0.1592<br>0.2019<br>0.4372<br>0.2192<br>0.1830<br>0.2022<br>0.3956<br>0.2115<br>0.1780<br>0.1961<br>0.4144<br>0.2165<br>0.1724<br>0.2206<br>0.3904<br>0.2099<br>0.1687<br>0.2136<br>0.4079|
||4<br>0.1552<br>0.1854<br>0.1593<br> **0.0000**<br> **0.0000**<br>0.0968<br>0.0825<br>0.0944<br>0.1666<br>0.1545<br>0.1752<br> **0.0000**<br> **1.0000**<br>0.6774<br>0.6394<br>0.6191<br>4<br>0.2210<br>0.2354<br>0.2244<br> **0.0000**<br> **0.0000**<br>0.1799<br>0.1732<br>0.1807<br>0.2304<br>0.2240<br>0.2338<br> **0.0000**<br> **1.0000**<br>0.4168<br>0.3956<br>0.3904|
|(12_,_ 0)|1<br>2<br>3<br>0.5778<br>0.1770<br>0.0900<br>0.5358<br>0.1793<br>0.0995<br>0.6061<br>0.1532<br>0.0813<br>**1.0000 0.0000 0.0000 **<br>**0.0000 1.0000 0.0000 **<br>0.1753<br>0.5352<br>0.1927<br>0.1581<br>0.5958<br>0.1636<br>0.1786<br>0.5473<br>0.1796<br>0.0876<br>0.1382<br>0.6076<br>0.0894<br>0.1518<br>0.6043<br>0.0934<br>0.1447<br>0.5868<br>**0.0000 0.0000 1.0000 **<br>**0.0000 0.0000 0.0000 **<br>0.1271<br>0.0680<br>0.1274<br>0.1459<br>0.0830<br>0.1317<br>0.1437<br>0.0824<br>0.1547<br>1<br>2<br>3<br>0.3627<br>0.2375<br>0.1787<br>0.3475<br>0.2331<br>0.1840<br>0.3745<br>0.2298<br>0.1714<br>**1.0000 0.0000 0.0000 **<br>**0.0000 1.0000 0.0000 **<br>0.2312<br>0.3375<br>0.2515<br>0.2256<br>0.3610<br>0.2401<br>0.2327<br>0.3552<br>0.2315<br>0.1825<br>0.2081<br>0.3790<br>0.1848<br>0.2141<br>0.3771<br>0.1879<br>0.2100<br>0.3683<br>**0.0000 0.0000 1.0000 **<br>**0.0000 0.0000 0.0000 **<br>0.2097<br>0.1635<br>0.2100<br>0.2192<br>0.1830<br>0.2022<br>0.2165<br>0.1724<br>0.2206|
|(0_,_ 8)|1<br>2<br>3<br>4<br>0.5570<br>0.1876<br>0.0923<br>0.1631<br>0.5161<br>0.1878<br>0.1016<br>0.1945<br>0.5846<br>0.1625<br>0.0834<br>0.1695<br>**1.0000 0.0000 0.0000 0.0000**<br>**0.0000 1.0000 0.0000 0.0000**<br>0.1833<br>0.5154<br>0.2025<br>0.0987<br>0.1676<br>0.5741<br>0.1738<br>0.0845<br>0.1875<br>0.5276<br>0.1885<br>0.0963<br>0.0905<br>0.1460<br>0.5856<br>0.1780<br>0.0923<br>0.1611<br>0.5827<br>0.1639<br>0.0963<br>0.1523<br>0.5648<br>0.1865<br>**0.0000 0.0000 1.0000 0.0000**<br>**0.0000 0.0000 0.0000 1.0000**<br>0.1381<br>0.0710<br>0.1385<br>0.6524<br>0.1575<br>0.0867<br>0.1411<br>0.6147<br>0.1534<br>0.0854<br>0.1660<br>0.5952<br>1<br>2<br>3<br>4<br>0.3476<br>0.2443<br>0.1817<br>0.2264<br>0.3343<br>0.2382<br>0.1866<br>0.2408<br>0.3579<br>0.2368<br>0.1743<br>0.2310<br>**1.0000 0.0000 0.0000 0.0000**<br>**0.0000 1.0000 0.0000 0.0000**<br>0.2361<br>0.3240<br>0.2578<br>0.1821<br>0.2321<br>0.3441<br>0.2478<br>0.1760<br>0.2382<br>0.3419<br>0.2366<br>0.1833<br>0.1862<br>0.2135<br>0.3628<br>0.2375<br>0.1886<br>0.2199<br>0.3613<br>0.2303<br>0.1916<br>0.2150<br>0.3528<br>0.2406<br>**0.0000 0.0000 1.0000 0.0000**<br>**0.0000 0.0000 0.0000 1.0000**<br>0.2177<br>0.1674<br>0.2181<br>0.3968<br>0.2268<br>0.1878<br>0.2082<br>0.3773<br>0.2230<br>0.1758<br>0.2276<br>0.3736<br>d.|
|(_β_1_, β_2)<br>(8_,_ 0)|cluster<br>1<br>2<br>3<br>4<br>1<br>0.5570<br>0.1876<br>0.0923<br>0.1631<br>2<br>0.5161<br>0.1878<br>0.1016<br>0.1945<br>3<br>0.5846<br>0.1625<br>0.0834<br>0.1695<br>4<br>**1.0000 0.0000 0.0000 0.0000**<br><br>5<br>**0.0000 1.0000 0.0000 0.0000**<br><br>6<br>0.1833<br>0.5154<br>0.2025<br>0.0987<br>7<br>0.1676<br>0.5741<br>0.1738<br>0.0845<br>8<br>0.1875<br>0.5276<br>0.1885<br>0.0963<br>9<br>0.0905<br>0.1460<br>0.5856<br>0.1780<br>10<br>0.0923<br>0.1611<br>0.5827<br>0.1639<br>11<br>0.0963<br>0.1523<br>0.5648<br>0.1865<br>12<br>**0.0000 0.0000 1.0000 0.0000**<br><br>13<br>**0.0000 0.0000 0.0000 1.0000**<br><br>14<br>0.1381<br>0.0710<br>0.1385<br>0.6524<br>15<br>0.1575<br>0.0867<br>0.1411<br>0.6147<br>16<br>0.1534<br>0.0854<br>0.1660<br>0.5952<br>cluster<br>1<br>2<br>3<br>4<br>1<br>0.3476<br>0.2443<br>0.1817<br>0.2264<br>2<br>0.3343<br>0.2382<br>0.1866<br>0.2408<br>3<br>0.3579<br>0.2368<br>0.1743<br>0.2310<br>4<br>**1.0000 0.0000 0.0000 0.0000**<br><br>5<br>**0.0000 1.0000 0.0000 0.0000**<br><br>6<br>0.2361<br>0.3240<br>0.2578<br>0.1821<br>7<br>0.2321<br>0.3441<br>0.2478<br>0.1760<br>8<br>0.2382<br>0.3419<br>0.2366<br>0.1833<br>9<br>0.1862<br>0.2135<br>0.3628<br>0.2375<br>10<br>0.1886<br>0.2199<br>0.3613<br>0.2303<br>11<br>0.1916<br>0.2150<br>0.3528<br>0.2406<br>12<br>**0.0000 0.0000 1.0000 0.0000**<br><br>13<br>**0.0000 0.0000 0.0000 1.0000**<br><br>14<br>0.2177<br>0.1674<br>0.2181<br>0.3968<br>15<br>0.2268<br>0.1878<br>0.2082<br>0.3773<br>16<br>0.2230<br>0.1758<br>0.2276<br>0.3736<br>Note: Medoids’ membership degrees are in bol|



43 

|**Data**<br>**configuration**|8, 0|(0, 8)|(12, 0)|(_β_1_, β_2<br>(0, 12)|)<br>(16, 0)|(0, 16)|(20, 0)|(0, 20)|
|---|---|---|---|---|---|---|---|---|
|1)|0.90|0.89|0.90|0.89|0.90|0.89|0.90|0.89|
|2)|0.84|0.82|0.84|0.82|0.84|0.82|0.84|0.82|
|3)|0.56|0.60|0.57|0.57|0.58|0.58|0.84|0.75|
|4)|0.16|0.16|0.23|0.23|0.26|0.26|0.29|0.29|



Table A.12: Fuzzy Silhouette index values for simulation study 2 according to different setting of the parameters _β_ 1 _, β_ 2 (column wise) and to data configuration (row wise) 

44 

