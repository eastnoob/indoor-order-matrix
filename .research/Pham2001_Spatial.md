Computer Vision and Image Understanding **84,** 285–297 (2001) doi:10.1006/cviu.2001.0951, available online at http://www.idealibrary.com on 



# Spatial Models for Fuzzy Clustering 

Dzung L. Pham 

_Laboratory of Personality and Cognition, Gerontology Research Center, NIA/NIH, 5600 Nathan Shock Drive, Baltimore, Maryland 21224_ E-mail: dzung.pham@nih.gov 

Received May 25, 2001; accepted November 20, 2001 

A novel approach to fuzzy clustering for image segmentation is described. The fuzzy _C_ -means objective function is generalized to include a spatial penalty on the membership functions. The penalty term leads to an iterative algorithm that is only slightly different from the original fuzzy _C_ -means algorithm and allows the estimation of spatially smooth membership functions. To determine the strength of the penalty function, a criterion based on cross-validation is employed. The new algorithm is applied to simulated and real magnetic resonance images and is shown to be more robust to noise and other artifacts than competing approaches. ⃝c 2001 Elsevier Science (USA) 

_KeyWords:_ fuzzyclustering;fuzzyc-means;imagesegmentation;Markovrandom fields; cross-validation. 

## **1. INTRODUCTION** 

The fuzzy _C_ -means algorithm (FCM) has been utilized in a wide variety of image processing applications such as medical imaging [1, 2] and remote sensing [3, 4]. Its advantages include a straightforward implementation, fairly robust behavior, applicability to multichannel data, and the ability to model uncertainty within the data. A major disadvantage of its use in imaging applications, however, is that FCM does not incorporate information about spatial context, causing it to be sensitive to noise and other imaging artifacts. 

Mathematically,FCMisderivedtominimizethefollowingobjectivefunctionwithrespect to the membership functions _u jk_ and the centroids _vk_ 



where _y j_ is the observation at pixel _j, C_ is the number of clusters or classes, and _�_ is the 

285 

1077-3142/01 $35.00 ⃝c 2001 Elsevier Science (USA) All rights reserved. 

286 

DZUNG L. PHAM 



**FIG. 1.** Fuzzy c-means results for different values of the _q_ parameter: (a) slice from MR image of the brain, (b) FCM membership function corresponding to gray matter tissue for _q_ = 1 _._ 2, (c) FCM membership function for _q_ = 2, (d) FCM membership function for _q_ = 3. 

image domain. The membership functions are constrained to be positive and to satisfy 



Here, the objective function is minimized when high membership values are obtained in areas where the observations are close to the centroid, and low membership values are obtained where observations are distant from the centroid. The parameter _q_ is a weighting exponent that satisfies _q >_ 1 and controls the degree of “fuzziness” in the resulting membership functions. As _q_ approaches unity, the membership functions become more crisp, and approach binary functions. As _q_ increases, the membership functions become increasingly fuzzy. Figure 1 shows the results of applying FCM to a magnetic resonance (MR) image of the brain as the parameter _q_ is increased. 

Itisapparentfrom(1)thattheFCMobjectivefunctiondoesnottakeintoconsiderationany spatial dependence between observations. Thus, the computed membership functions can exhibit a sensitivity to noise in the observed image. One obvious approach to compensate for this sensitivity is to smooth the image before applying FCM. However, standard smoothing filters can result in a loss of important image details. More importantly, there is no way to rigorously control the trade-off between the smoothing and the clustering result that is obtained. Other approaches for obtaining spatially smooth membership functions include postprocessing the membership functions [5, 6] or incorporating multiscale information to enforce spatial constraints [4, 7, 8]. Recently, an approach was proposed for increasing the robustness of FCM to noise by directly modifying the objective function [9]. The normed distance computed at each pixel within the image was replaced with a weighted sum of distances within a neighborhood of the pixel. Of the aforementioned approaches, this latter one is the most similar to this work. The formulation of [9], however, leads to a rather counterintuitive equation for computing class centroids and the overall methodology may be difficult to incorporate into some FCM-based applications. 

A more classical approach to incorporating spatial information is to penalize the FCM objective function to constrain the behavior of the membership functions, similar to methods used in regularization and Markov random field (MRF) theory [10]. This penalty can be used to discourage unlikely or undesirable configurations in the membership functions, such as a high membership value immediately surrounded by low values of the same class. An 

287 

SPATIAL MODELS FOR FUZZY CLUSTERING 

advantage of using a penalty function is that only the computations involving membership values is changed—centroid computations are the same as in standard FCM. This kind of approach was adopted in [11], which used standard first order differences as a penalty to force membership values to be similar to neighboring values. The main problem with such a penalty function, however, is that it can drastically alter the characteristics of the membership function in an undesirable fashion. For example, first order differences will cause membership functions to be nearly piecewise constant. Second order differences will cause membership functions to be more smooth. However, depending on the value of the _q_ parameter, this may contradict the desired characteristics of the membership functions. 

In this paper, a new objective function is proposed for incorporating spatial context into FCM. The objective function includes a penalty term that is reminiscent of MRF priors but is consistent with the desired behavior of the membership functions dictated by the value of the _q_ parameter. The algorithm for minimizing the new objective function, called the Robust Fuzzy _C_ -means Algorithm (RFCM), possesses improved robustness to noise over FCM. An advantage of RFCM is that its equations are only slightly different from the original FCM equations. Furthermore, other variants of FCM (cf. [12, 13]) should also benefit from the proposed spatial model. It is shown that the strength of the penalty term can be selected using a criterion based on cross-validation. Results are shown applying the new algorithm to real and simulated magnetic resonance images. Throughout this paper, it will be assumed that the total number of clusters, _C_ , is known. Methods based on FCM for determining the number of clusters [14, 15], however, can be applied to this work in a straightforward manner. 

## **2. THEORY** 

In this section, a new objective function is proposed for fuzzy clustering with spatially constrained membership functions and an algorithm is derived for minimizing this objective function. 

## _2.1. Penalized FCM_ 

In order to restrict the membership functions in FCM to be spatially smooth, the following objective function is proposed 



where _N j_ is the set of neighbors of pixel _j_ , and _Mk_ = {1 _, . . . , C_ }\{ _k_ }. The parameter _β_ controls the trade-off between minimizing the standard FCM objective function and obtaining smooth membership functions. Appropriate selection of this parameter is described in Section 2.2. 

The new penalty term is minimized when the membership value for a particular class is large and the membership values for the other classes at neighboring pixels is small (and vice versa). In other words, it constrains the membership value of a class to be negatively correlated with the membership values of the other classes at neighboring pixels. Figure 2 illustrates the role of the penalty function for different values of _q_ . In both plots, the penalty of a single pairwise interaction is minimized when one or both membership functions are 

288 

DZUNG L. PHAM 



<!-- Start of picture text -->
2 2<br>ujkulm ujkulm<br>1 1<br>0.8 0.8<br>0.6 0.6<br>0.4 0.4<br>0.2 0.2<br>0 0<br>1 1<br>0.8 1 0.8 1<br>0.6 0.8 0.6 0.8<br>ulm 0.4 0.2 0.2 0.4 u 0.6 jk ulm 0.4 0.2 0.2 0.4 u 0.6 jk<br>0 0 0 0<br>(a) (b)<br><!-- End of picture text -->

**FIG. 2.** Magnitude of the penalty function for different values of _q_ : (a) plot of _u jk ulm_ , (b) plot of _u_<sup>2</sup> _jk_<sup>_u_</sup> _lm_<sup>2.</sup> 

zero, and maximized when both values are unity. Thus, configurations where adjacent pixels have high membership values in different classes are discouraged. When _q_ = 2 there is a larger region of the plot where a relatively low penalty is obtained. This allows for the existence of membership values which are not necessarily binary, and is consistent with the role of _q_ in the standard FCM formulation. Note that the penalty term is similar to the energy terms used in MRF prior probability models [16]. The major differences are that here, _u jk_ are continuously valued variables and the parameter _q_ is included to regulate the “fuzziness” of the neighborhood interactions. 

An iterative algorithm for minimizing (3) can be derived by evaluating the centroids and membership functions that satisfy a zero gradient condition. Using Lagrange multipliers to enforce the constraint in (2) and taking the partial derivative of (3) with respect to _u jk_ yields 



where the factor of<sup><u>1</u></sup> 2<sup>on</sup><sup>_β_vanishesbecausethederivativeoperatorresultsinaterm</sup> corresponding to the product of _u jk_ and its neighbors, plus a term corresponding to the reverse product of the neighbors and _u jk_ . Setting this partial derivative to zero yields 



To solve for _λ j_ , the constraint equation (2) is employed, yielding 



289 

SPATIAL MODELS FOR FUZZY CLUSTERING 

Because _λ j_ does not depend on _k_ , it can be factored out of the summation, leading to 



Combining Eqs. (5) and (7) results in the following necessary condition for _u jk_ to be at a local minimum of _JRFCM_ 



The presence of the _q_ parameter within the penalty function allows for an elegant expression to be obtained for _u jk_ . Using a different exponent value would yield a considerably more complicated equation. When _β_ = 0, Eq. (8) is identical to the standard FCM equation for computing membership values. When _β >_ 0, the dependency on the neighbors causes _u jk_ to be large when the neighboring membership values of other classes is small. Conversely, if the neighboring membership values are small, the membership value at _u jk_ is increased. The result is a smoothing effect that causes neighboring membership values in the same class to be similar to one another. Note that the positivity condition on all membership values is satisfied by (8). 

Because the penalty function does not depend on _vk_ , the necessary conditions on the centroids for (3) to be minimized is identical to that of FCM [17]. Iteration through these necessary conditions results in an algorithm for minimizing the objective function that is almost identical to standard FCM. The steps are as follows: 

ALGORITHM 1. Robust Fuzzy C-means Algorithm 

1. Obtain initial estimates of the centroids, _vk_ . 

2. Compute membership functions using (8). 

3. Compute centroids: 



4. Go to step 2 and repeat until convergence. 

For scalar imaging data, Step 1 can be performed automatically using the histogram smoothing method described in [18]. Convergence can be considered to be obtained when the change in the objective function is less than some threshold, or when the change in the membership values is less than some threshold. The latter criterion is used in this paper. Figure3showstheresultsofapplyingRFCMtothesameimageshowninFig.1afordifferent values of _q_ and _β_ . Compared to the standard FCM results in Fig. 1, the spatial constraint clearly causes a smoothing effect. However, the effect is consistent with the selection of _q_ . Figures 3b and 3c show that for _q_ = 2, even when the _β_ parameter is significantly increased, the membership function does not become binarized. 

Based on the results of [17] and because the penalty function is independent of the centroids, Step 3 of RFCM is guaranteed to decrease the objective function (3). To show that the computation in Step 2 will also decrease the objective function, it is sufficient to 

290 

DZUNG L. PHAM 



**FIG. 3.** RFCM membership function corresponding to gray matter for different values of _β_ and _q_ : (a) _β_ = 100 and _q_ = 1 _._ 2, (b) _β_ = 100 and _q_ = 2, (c) _β_ = 250 and _q_ = 2 , (d) _β_ = 100 and _q_ = 3. 

show that the Hessian matrix with respect to _u j_ 1 _, . . . , ujC_ is positive definite for each pixel _j_ . This _C_ × _C_ matrix will be diagonal, with diagonal elements _dk_ that satisfy 



By substituting (8) for _u jk_ and assuming that ∥ **y** _j_ − **v** _k_ ∥ _>_ 0, each _dk_ must be strictly positive and therefore the Hessian matrix will be positive definite. Together, these properties guarantee that the RFCM objective function must decrease with each iteration of the algorithm. 

Straightforward generalizations to the penalty function in (3) are possible. For example, interactions between certain classes may be stronger than others. Furthermore, when pixels or voxels are not isotropic in size, it maybe desirable to vary the strength of interactions along different coordinate axes. A more general penalty function is 



where **u** _j_ = [ _u_<sup>_q_</sup> _j_ 1<sup>_, . . . , uq_</sup> _jC_<sup>]</sup><sup>_, V_isasymmetricmatrixwithzeroentriesalongthediagonal</sup> and positive entries elsewhere, and _βl_ now varies with respect to the direction of the neighbor being considered. 

Note that in this work, the value of _β_ does not vary with the local characteristics of the image. It may, in some applications, be desirable to adjust _β_ according to certain image features, such as edges, to prevent smoothing of those features. Currently, pixels at step edges will incur a slight penalty in favor of other classes. Unlike typical noisy pixels, however, there will still be some neighbors of the same class. In addition, natural images tend to have softer edges and thus, the magnitude of the penalty will be smaller since pixels in between classes will have low membership values for all classes. The effects of edges on RFCM is demonstrated in Section 3, where it is shown that edges are generally still preserved even with a fixed _β_ , when appropriately selected. 

## _2.2. Selection of β_ 

Proper selection of the _β_ parameter is important for obtaining optimal or near-optimal performance. Determination of an appropriate value of _β_ is dependent on the image being clustered. It is apparent from (3) and (8) that the value depends on the brightness of the 

291 

SPATIAL MODELS FOR FUZZY CLUSTERING 

image as well as the variation of the intensity values relative to the centroid values of each class. In this section, a criterion based on cross-validation is described for choosing an appropriate value of _β_ . 

Cross-validation is a well-studied method for selection of a regularization parameter in solving discrete ill-posed problems [19]. The basic premise of cross-validation is that the data is split into a validation set and a data set. The algorithm under study is applied to the data set for a fixed value of the unknown parameter, where the data points corresponding to the validation set are assumed to be missing. The validation set is then used to test the appropriateness of the parameter selection by computing a cross-validation error. The process is repeated for different values of the parameter, and the parameter value that yields the lowest cross-validation error is considered to be optimal. In a sense, cross-validation selects the parameter that allows the data set to best estimate or interpolate the validation set. 

In true cross-validation schemes, the validation set is chosen to be one pixel, the error is computedforthatonepixel,andthisprocessisrepeatedforeverypixelintheimage.Thetotal cross-validation error is defined to be the sum of the errors resulting from using each pixel as a validation set. When the model is nonlinear and the size of the data is large, true crossvalidation can be computationally intensive since the algorithm must be reapplied _N_ times, where _N_ is the total number of pixels in the image. As an alternative, the _holdout method_ [20] is used in this work, where the validation set consists of a fixed subsampling of pixels, and the algorithm is applied only once to compute the cross-validation error over that set of pixels. 

In the case of RFCM, the estimated membership values within the validation set as well as the centroids should satisfy the same criteria as the values within the data set. The cross-validation error can therefore be defined to be 



where _�v_ is the validation set using the holdout method. The RFCM algorithm using crossvalidation is as follows: 

ALGORITHM 2. RFCM using cross-validation 

1. Apply FCM (or RFCM with _β_ = 0) to the image. 

2. Compute _βinc_ = 0 _._ 1 ∗ ( _JRFCMJ_ − _<u>FCMJFCM</u>_ ) _/β_<sup>.</sup> 

3. Set _β_ = _βinc_ . 

4. Apply RFCM to the data set. 

5. Compute _Ecv_ on validation set. 

6. Set _β_ = _β_ + _βinc_ , and go to Step 4, using the current result as an initialization of the 

next application of RFCM. 

7. Apply RFCM to entire image using the value of _β_ that minimizes _Ecv_ . 

Step 2 is a rule of thumb that simply increments _β_ by 10% of the ratio of the data term to the penalty term in (3). In Step 3, the validation set is assumed to be missing, so the membership values at those locations are computed using the values of the neighboring membership values. In most situations, the cross-validation error is very well behaved for different values of _β_ and the algorithm can be terminated when the first local minimum is found. Figure 4 shows a typical plot of the cross-validation error computed for various values of _β_ when applying RFCM to an image. In this example, the error is minimized for 

292 

DZUNG L. PHAM 



<!-- Start of picture text -->
3.2e+05<br>3.15e+05<br>3.1e+05<br>3.05e+05<br>3e+05<br>0 100 200 300 400 500 600<br>β<br>Cross validation error<br><!-- End of picture text -->

**FIG. 4.** Plot of cross-validation error for different values of _β_ . 

_β_ ≈ 260 and the curve is nearly convex, although an additional local minimum is present where _β_ is very large. Note that using 10% of the ratio of the energy terms in Step 2 was determined empirically. In some cases, the step size may be too large and local minima might still be missed by the algorithm. 

## **3. RESULTS** 

In this section, the results of applying RFCM to real and simulated images are shown. For the results on magnetic resonance imaging data, the algorithms were applied to threedimensional images and the first-order, six voxel neighborhood system was used for the spatial penalty term in RFCM. In these experiments, _q_ = 2 and _C_ = 3, where the three classes correspond to gray matter, white matter, and cerebrospinal fluid in the brain. All images were eight bit and background pixels were ignored. The algorithms were implemented in C on a 1 GHz PC system running Linux. Execution times varied according to the size of the image and amount of noise. Noisier images increased the amount of time required for both estimating _β_ and for convergence of the clustering algorithm. For the two-dimensional results, total execution time was approximately 30 s. For the three-dimensional scalar images (approximately 180 × 180 × 180 voxels), execution times varied from 4 to 12 min to estimate _β_ , and 40 s to 3.5 min to perform the final clustering. As a comparison, standard FCM required approximately 20 s when applied to the same images. 

Figure 5 displays the results of FCM and RFCM when applied to a two-dimensional synthetic test image. The test image possesses four classes with intensity values 0, 25, 50, and 75, and the image size is 96 × 96 pixels. White Gaussian noise with a standard deviation of 10 was added to the image. Figure 5a shows the test image and Figs. 5b and 5c show the results of the maximum membership classification produced by standard FCM and RFCM, respectively. A maximum membership classification is simply the assignment of a pixel to the class of highest membership. The value of _β_ was determined by the cross-validation method using the first found local minimum and was found to be approximately 435. The RFCM classification is clearly much more robust to the presence of noise than the FCM 

293 

SPATIAL MODELS FOR FUZZY CLUSTERING 













<!-- Start of picture text -->
(a) (b) (c) (d) (e)<br><!-- End of picture text -->

**FIG. 5.** FCM and RFCM applied to a two-dimensional test image: (a) test image, (b) FCM maximum membership classification, (c) RFCM classification, (d) FCM membership function, (e) RFCM membership function. 

classification. The misclassification rate (MCR), computed by 



was 14.14 and 0.52% for FCM and RFCM, respectively. 

Figures 5d and 5e show the membership function generated by FCM and RFCM corresponding to the class with the second brightest intensity. These figures illustrate the effect of the neighborhood interactions on the computation of membership values. The RFCM result is obviously smoother and less speckled. It is also possible to see that there is a faint artifact induced at edges within the image. This is caused by the influence of the penalty function in neighborhoods containing pixels from different classes. Because edges do not conform to the assumption that neighboring pixels should be similar, the membership value of the actual class is lowered slightly, thereby slightly increasing the membership values for other classes. 

Figure 6 shows the application of RFCM to a real multichannel MR image. Figures 6a and 6b show one slice taken from a dual spin–echo MR image of the brain. The images have been preprocessed to extract the intracranial volume. Figures 6c and 6d are the maximum membership classification obtained using FCM and RFCM, respectively. The cross-validation criterion was used to automatically select the amount of smoothing performed in RFCM, resulting in a value of _β_ approximately equal to 80. The RFCM classification exhibits less speckling and the segmented tissues have smoother boundaries. Figures 6e–6h show the membership functions computed by FCM and RFCM for gray matter and white matter tissue types. Again, the smoother appearance of the RFCM results is evident, and fine details of the anatomy are still preserved. 

Figure 7 shows some results of applying RFCM to a simulated MR image taken from the Brainweb database [21]. An MR image was simulated with 1-mm cubic voxels, 5% noise, and no inhomogeneity. For selection of _β_ , every tenth voxel along each dimension was used as the validation set. Figure 7a shows the true hard classification used to simulate the image. The RFCM maximum membership classification shown in Fig. 7b is very close to the truth model. Figure 7c is the gray matter partial volume model used to simulate the MR image and Fig. 7d is the RFCM gray matter membership function. As has been reported previously in the literature [22], fuzzy clustering algorithms can be used to estimate partial volumes and Fig. 7d shows that RFCM obtains a reasonable reconstruction of the true partial volume fractions. Figures 7e and 7f show surfaces computed using FCM and RFCM that roughly correspond to the gray matter–white matter boundary. The surfaces were constructed using an isosurface algorithm computed on the white matter membership function at a value of 

294 

DZUNG L. PHAM 



**FIG. 6.** FCM and RFCM applied to dual spin–echo MR images: (a) Proton density weighted image, (b) T2weighted image, (c) FCM maximum membership classification, (d) RFCM maximum membership classification, (e) FCM gray matter membership, (f) RFCM gray matter membership, (g) FCM white matter membership, (h) RFCM white matter membership. 



**FIG. 7.** Results on a simulated T1-weighted MR image: (a) true hard classification, (b) RFCM maximum membership classification, (c) true gray matter partial volume image, (d) RFCM gray matter membership, (e) surface of gray matter/white matter interface computed from FCM white matter membership, (f) surface computed from RFCM white matter membership. 

295 

SPATIAL MODELS FOR FUZZY CLUSTERING 

**TABLE 1** 

**Error Measures from Simulated MR Results** 

||Misci|lassification|Noise lev<br>i Rate|el/Error<br>Ave|rage RMS E|rror|
|---|---|---|---|---|---|---|
|Method-Error|3%Noise|5%Noise|7%Noise|3%Noise|5%Noise|7%Noise|
|Optimal RFCM|3.761%|4.956%|6.047%|0.1188|0.1388|0.1587|
|CV RFCM|3.785%|5.017%|6.067%|0.1200|0.1394|0.1586|
|Standard FCM|3.988%|6.601%|10.249%|0.1302|0.1728|0.2208|
|FCM w/Med. filt.|6.930%|7.344%|7.881%|0.1825|0.1868|0.1930|
|FCM w/Opt. AD filt.|3.760%|5.188%|6.516%|0.1277|0.1524|0.1726|



0.5. These figures clearly illustrate how RFCM is more robust than FCM, yielding smoother and more realistic boundaries. 

Table 1 shows the error values obtained when applying several different algorithms to the simulated images for different levels of noise. Two error measures were used: MCR (see Eq. (12)) and the average root mean squared (RMS) error of the membership functions. The RMS error is computed between the estimated membership value and the true partial volumefractions.Thesumoftheerrorsoverthethreedifferentclassesdividedbythreeyields the average RMS error. _Optimal RFCM_ refers to RFCM applied to the images multiple times using different values of _β_ , and selecting the result that yielded the lowest misclassification rate. In other words, _β_ was chosen with prior knowledge of the truth models. _CV RFCM_ refers to RFCM using the cross-validation criterion to select _β_ . _Standard FCM_ refers to FCM with no smoothing applied. _FCM w/ Med. Filt_ . refers to FCM applied to images that have been prefiltered with a 3 × 3 × 3 median filter. Finally, _FCM w/ Opt. AD filt_ . refers to FCM applied to images that have been prefiltered with anisotropic diffusion, where “Opt.” is an abbreviation for “Optimal.” The smoothing parameter and the number of iterations of the anisotropic diffusion were selected by running the diffusion and FCM with multiple values and selecting the values that yielded the lowest misclassification rate. 

As expected, an increase in the level of noise always led to an increase in the errors for all methods. The RFCM methods were most robust to increased noise, however. When comparing the optimal _β_ to the _β_ selected using cross-validation for RFCM, it was found that cross-validation consistently underestimated _β_ . The optimal values of _β_ were empirically found to be 75, 200, and 300 for the 3, 5, and 7% noise cases, respectively. The values of _β_ determined using GCV were approximately 55, 150, and 260, respectively. This problem with cross-validation has been noted under other models as well [23, 24]. Despite this underestimation, the final errors are extremely close. Standard FCM performs quite well for low levels of noise but its performance rapidly degrades as noise is increased. The median filter results demonstrate what can occur when blindly applying filtering to remove noise. At the 3 and 5% noise levels, the median filter oversmoothed the image, increasing the errors over even the standard FCM method. The use of FCM in tandem with anisotropic diffusion results in substantial improvements over FCM and is comparable to RFCM in terms of misclassification rate. Because anisotropic diffusion tends to converge to images that are nearly piecewise constant however, its average RMS are all higher than the RFCM errors. In addition, appropriate selection of the number of iterations and smoothing parameter 

296 

DZUNG L. PHAM 

was difficult. Small changes in those values sometimes led to large increases in error. Nevertheless, one might interpret the errors as saying that RFCM is operating in a manner somewhat similar to anisotropic diffusion. 

## **4. CONCLUSIONS** 

This work describes a natural extension of FCM to incorporate spatial constraints on the membershipfunctions.Thenewformulationshouldproveextremelybeneficialtoimproving the performance of fuzzy clustering algorithms in image processing applications. This is especially true because the penalty function can be applied in a straightforward manner to nearly all variants of FCM, such as the adaptive fuzzy _C_ -means algorithm [13] and the possibilistic _C_ -meansalgorithm[12],withminimalchangestotheresultingimplementation. 

## **ACKNOWLEDGMENTS** 

The author thanks Jerry Prince, Chenyang Xu, Xiao Han, Maryam Rettmann, Susan Resnick, and Alan Zonderman for their thoughtful comments and suggestions. The author also thanks Dr. Xu for his implementation of the three-dimensional anisotropic diffusion and median filtering algorithms. 

## **REFERENCES** 

1. D. L. Pham, J. L. Prince, A. P. Dagher, and C. Xu, An automated technique for statistical characterization of brain tissues in magnetic resonance imaging, _Int. J. Pattern Recognit. Artificial Intell._ , to appear (Tech. Rep. JHU/ECE 96–13). 

2. J. C. Bezdek, L. O. Hall, and L. P. Clarke, Review of MR image segmentation techniques using pattern recognition, _Med. Phys_ . **20** , 1993, 1033–1048. 

3. E. Rignot, R. Chellappa, and P. Dubois, Unsupervised segmentation of polarimetric SAR data using the covariance matrix, _IEEE Trans. Geosci. Remote Sensing_ **30** (4), 1992, 697–705. 

4. W. Chumsamrong, P. Thitimajshima, and Y. Rangsanseri, Syntetic aperture radar (SAR) image segmentation using a new modified fuzzy c-means algorithm, in _Proceedings of Geoscience and Remote Sensing Symposium_ , Vol. 2, pp. 624–626, 2000. 

5. Y. A. Tolias and S. M. Panas, On applying spatial constraints in fuzzy image clustering using a fuzzy rule-based system, _IEEE Signal Process. Lett_ . **5** (10), 1998, 245–247. 

6. A. Pardo and G. Sapiro, Vector probability diffusion, in _Proceedings of the 2000 Int’l Conf. on Image Processing_ , Vol. 1, pp. 884–887, 2000. 

7. Y. A. Tolias and S. M. Panas, Image segmentation by a fuzzy clustering algorithm using adaptive spatially constrained membership functions, _IEEE Trans. Systems, Man, Cybernet. A_ **28** (3), 1998, 359–369. 

8. S. T. Acton and D. P. Mukherjee, Scale space classification using area morphology, _IEEE Trans. Image Process_ . **9** (4), 2000, 623–635. 

9. A. W. C. Liew, S. H. Leung, and W. H. Lau, Fuzzy image clustering incorporating spatial continuity, _IEE Proc. Visual Image Signal Process_ . **147** (2), 2000, 185–192. 

10. S. Geman and D. Geman, Stochastic relaxation, Gibbs distributions, and the Bayesian restoration of images, _IEEE Trans. Pattern Anal. Machine Intell_ . **6** , 1984, 721–741. 

11. R. Castagno, T. Ebrahimi, and M. Kunt, Video segmentation based on multiple features for interactive multimedia applications, _IEEE Trans. Circuits Systems Video Technol_ . **8** (5), 1998, 562–571. 

12. R. Krishnapuram and J. M. Keller, A possibilistic approach to clustering, _IEEE Trans. Fuzzy Systems_ **1** (2), 1993, 98–110. 

13. D. L. Pham and J. L. Prince, Adaptive fuzzy segmentation of magnetic resonance images, _IEEE Trans. Med. Imaging_ **18** (9), 1999, 737–752. 

297 

SPATIAL MODELS FOR FUZZY CLUSTERING 

14. I. Gath and A. B. Geva, Unsupervised optimal fuzzy clustering, _IEEE Trans. Pattern Anal. Machine Intell_ . **11** (7), 1987, 773–781. 

15. X. L. Xie and G. Beni, A validity measure for fuzzy clustering, _IEEE Trans. Pattern Anal. Machine Intell_ . **13** (8), 1991, 841–847. 

16. J. Zhang, The mean field theory in EM procedures for Markov random fields, _IEEE Trans. Signal Process_ . **40** (10), 1992, 2570–2583. 

17. J. C. Bezdek, A convergence theorem for the fuzzy ISODATA clustering algorithms, _IEEE Trans. Pattern Anal. Machine Intell_ . **2** , 1980. 

18. D. L. Pham and J. L. Prince, An adaptive fuzzy c-means algorithm for image segmentation in the presence of intensity inhomogeneities, _Pattern Recognit. Lett_ . **20** (1), 1999, 57–68. 

19. G.Wahba, _SplineModelsforObservationalData_ ,SeriesinAppliedMathematics,Vol.59,SIAM,Philadelphia, PA, 1990. 

20. S. J. Reeves, A cross-validation framework for solving image restoration problems, _J. Visual Comm. Image Represent_ . **3** , 1992, 433–445. 

21. D. L. Collins, A. P. Zijdenbos, V. Kollokian, J. G. Sled, and N. J. Kabani, _et al_ ., Design and construction of a realistic digital brain phantom, _IEEE Trans. Med. Imaging_ **17** , 1998, 463–468. [See http://www. bic.mni.mcgill.ca/brainweb] 

22. M. E. Brandt, T. P. Bohan, L. A. Kramer, and J. M. Fletcher, Estimation of CSF, white and gray matter volumes in hydrocephalic children using fuzzy clustering of MR images, _Comput. Med. Imaging Graphics_ **18** , 1994, 25–34. 

23. A. M. Thompson, J. C. Brown, J. W. Kay, and D. M. Titterington, A study of methods of choosing the smoothing paramter in image restoration by regularization, _IEEE Trans. Pattern Anal. Machine Intell_ . **13** (4), 1991, 326–339. 

24. N. P. Galatsanos and A. K. Katsaggelos, Methods for choosing the regularization parameter and estimating the noise variance in image restoration and their relation, _IEEE Trans. Image Process_ . **1** (3), 1992, 322–336. 

