# High-Pressure Powder Data Interpretation — Source Notes

*Instrument-scientist domain notes (Malcolm Guthrie, 2026-04-30).  
These are the primary source for SKILL.md in this directory.*

---

interpretation of high pressure powder data skill 

The nature of high pressure (and more generally many other in situ or in operando) diffraction measurements invariably results in challenging datasets. This skill summarizes specific instances provides answers to how to identify and how to manage through both physical intervention in the experimental process and during subsequent analysis.

## Variable structure

One of the most important consequence of high pressure is that it can dramatically modify structure. This can span the gamut from delicate tuning of a bondlength or angle through to wholesale restructuring via phase transitions. Most structural databases are dominated by ambient pressure structures so, at best, should be treated as a starting point for any analysis of in situ high-pressure data. Importantly for Rietveld analysis, this essentially demands pre-indexing of the as-measured lattice to provide a sufficiently accurate starting point for the refinement. This can be non-trivial for lower symmetry phases of, for example, in layered structures where compression can be highly anistropic causing some Bragg peaks to move more than others. Beyond refinements, there is also an impact on background extraction techniques that have to be aware of the location of Bragg peaks in order to deconvolve signal from background. 

## Multiple phases

Phase transitions, sample decomposition, the likely presence of auxiliary materials (e.g. pressure media of pressure calibrants) and potential contaminant Bragg scattering from the pressure cell can often lead to multiple phases in the sample. Where possible this should be mitigated at the experimental stage as the nature of powder diffraction signal means that scattering from all illuminated, materials and phases are all superimposed in the final pattern. During analysis, the approach is to include multiple phases in the Rietveld model. 

## Microstructural effects

During a high-pressure phase transition the experimenter has little control over the resultant microstructure. Powder averaging can be a problem if the phase studied crystallizes in large crystallites or preferred orientation, which violate the requirement of Rietveld analysis of unbiased sampling of all orientations. Experimental mitigations can include control of rate of pressure or temperature changes, introduction of crystallization "seeds" (e.g. silica wool or mesoporous materials) but these are all sample and phase dependent.

Subsequent Rietveld analysis has to take account of these effects in modelling. TOF conveys unique advantages for quantifying and modelling preferred orientation as it enables direct resolution of orientational domains. Pixel masking approaches can be used during reduction to remove scattering from anomalously large crystallites as their single-crystal peaks will skew the measured intensities. Where intensities are known to be unreliable, the information content of the diffraction signal is reduced to quantifying effects that can be derived from peak position or profile. Any resultant analysis should respect this intrinsic limitation of information, avoiding over analysis.

## Strain

It is very common for high pressure samples to experience strain gradients. Typically the neutron beam will sample an extended volume of the sample and average over all strain conditions. The net effect is a broadening of peaks. Typical experimental mitigation is to use a hydrostatic pressure medium (noble gases, deuterated alcohol mixtures and glycerin are examples). Annealing by heating to approximately 50% of the melting temperature can also greatly reduce stresses, sharpening peaks. However, this can also induce recrystallisation that degrades intensity reliability. 

An important advantage of TOF is that its angular resolution allows the resolution of angle-dependent strain, typically present in under a uniaxial load (such as a DAC or PE cell). Analysing this requires choice of pixels groupsing schemes that provide adequate angular resolution while retaining sufficient statistics for intensities to be extracted. 

Most Rietveld packages support fitting of strain and sample dependent peak broadening, but their support for TOF is patchy and full exploitation of the TOF information content is not typically possible at present     

## Sample Signal

An important characteristic of high pressure measurements is that the samples are small, necessitated by maximising force over area. Small samples mean that the net scattering signal is also small. Achieving sufficient counting statistics requires adequate exposure during the neutron measurement potentially extending to many hours in the case of the smallest samples which are found in DACs.

Another consideration is attenuation due to the pressure cell materials through which the beam passes. Any reduction of either incident or scattered beam will also degrade statistics (and any wavelength dependence must be properly accounted for during the reduction - cite reduction-SEE skill)   

## Background signal

Invariably the pressure cell will contribute background to the total measured signal. This background can be large (relative to the sample signal), structured and highly pressure dependent. The pressure dependence negates normal approach where an "empty cell" is measured and subtracted as the effects of pressure can't be replicated in this measurement. Typically all experimental steps possible should be taken to minize background (including careful collimation of the incident and diffracted beams).

In the analysis stage, Rietveld packages often have multiple models available for fitting backgrounds but these can struggle where there is a lot of structure in the background. This is all but intractable for DAC datasets due to multiple scattering of diamond reflections. The notching approach (cite) used during reduction can dramatically help with this, not only making the background much smoother but making it almost pressure independent, supporting measure-subtract approaches.

Another experimental technique is to amorphise or melt the sample, smearing out it's signal and leaving a usable approximation of the true background.

Often background scattering is structured. Very commonly, Bragg diffraction is seen from cell components such as anvils or gaskets. This should be minimized by experimental procedures but often will require additional elements to be added to the Rietveld models. As these cell components are usually proximous to the sample they are often also under significant loads making their contribution to the pattern pressure dependent too and therefore unsubtractable.   
