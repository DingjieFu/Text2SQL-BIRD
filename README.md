<div align="center">
<h1> Text2SQL for the BIRD dataset  </h1>
</div>

## Overview

This repository provides practice on text2SQL task (Understanding natural language and generating SQL queries).

## Summary

I primarily evaluated the performance of various LLMs (e.g., close-sourced DeepSeek and open-sourced Qwen series) on the BIRD-SQL benchmark. Specifically, my work focused on prompt engineering for effective database schema construction and post-processing techniques to select the optimal query from SQL candidates. Among the runs, utilizing `XiYanSQL-QwenCoder-32B-2504 + CSC-SQL` obtained the best 70.73% EX (Execute Accuracy) on the BIRD dev-set.

### Experiment
The experimental implementation can be categorized into two classes. First, I conducted API-based evaluations of DeepSeek-Chat (DeepSeek-V3-0324) to assess its SQL generation capabilities. As illustrated in Table, the standalone DeepSeek (57.69%) is not a satisfactory baseline method, demonstrating inferior performance compared to latest models: XiYanSQL (67.01%), Arctic-Text2SQL-R1 (72.20%), etc. Given that a high-capacity generator outperforms existing systems in this SQL generation tasks, XiYanSQL was selected as the foundational model. Some of the results are presented in Table. 


<table>
  <thead align="middle">
    <tr>
      <td rowspan="2"><b>Methods</b></td>
      <td colspan="4"><b>Dev(%)</b></td>
    </tr>
    <tr>
      <td><b>simple <br><span style="font-size: 10px"> 925</br></b></td>
      <td><b>moderate <br><span style="font-size: 10px"> 464</br></b></td>
      <td><b>challegnging <br><span style="font-size: 10px"> 145</br></b></td>
      <td><b>total <br><span style="font-size: 10px"> 1534</br></b></td>
    </tr>
  </thead>
  <tbody align="middle">
    <tr>
      <td> DeepSeek-V3-0324-wKg</td>
      <td> 56.32 </td>
      <td> 38.36 </td>
      <td> 32.41 </td>
      <td> 48.63 </td>
    </tr>
    <tr>
      <td>DeepSeek-V3-0324-wKg-Strict</td>
      <td> 63.35 </td>
      <td> 44.61 </td>
      <td> 35.17 </td>
      <td> 55.02 </td>
    </tr>
    <tr>
      <td>DeepSeek-V3-0324-MSchema-wKg-Strict</td>
      <td> 64.65 </td>
      <td> 48.92 </td>
      <td> 41.38 </td>
      <td> 57.69 </td>
    </tr>
    <tr>
      <td>DeepSeek-V3-0324-MSchema-wKg-Instruction</td>
      <td> 60.86 </td>
      <td> 41.16 </td>
      <td> 38.62 </td>
      <td> 52.80 </td>
    </tr>
    <tr>
      <td>DeepSeek-V3-0324-DDLSchemaLinks-wKg-Instruction</td>
      <td> 48.22 </td>
      <td> 32.97 </td>
      <td> 28.28 </td>
      <td> 41.72 </td>
    </tr>
    <tr>
      <td> --- </td>
      <td> --- </td>
      <td> --- </td>
      <td> --- </td>
      <td> --- </td>
    </tr>
    <tr>
      <td> XiYanSQL-QwenCoder-32B-2504_MSchema </td>
      <td> 72.00 </td>
      <td> 59.91 </td>
      <td> 53.79 </td>
      <td> 66.62 </td>
    </tr>
    <tr>
      <td> XiYanSQL-QwenCoder-32B-2504_SC-16g </td>
      <td> 73.30 </td>
      <td> 62.50 </td>
      <td> 51.72 </td>
      <td> 67.99 </td>
    </tr>
    <tr>
      <td> XiYanSQL-QwenCoder-32B-2504_CSCSQL-16g8m </td>
      <td> 74.81 </td>
      <td> 64.01 </td>
      <td> 53.79 </td>
      <td> 69.56 </td>
    </tr>
    <tr>
      <td> XiYanSQL-QwenCoder-32B-2504_CSCSQL-64g8m </td>
      <td> 75.68 </td>
      <td> 65.30 </td>
      <td> 56.55 </td>
      <td> 70.73 </td>
    </tr>
</table>

* Tips:
  1. DeepSeek-V3-0324-wKg-Strict: using prompt template: `Generate only the SQL query for the following requirement without any explanations, comments, or reasoning. \nBegin with ```sql, end with ``` `
  2.  DeepSeek-V3-0324-MSchema-wKg-Strict: ultilizing MSchema to substitute the default DDL-Schema
  3.  DeepSeek-V3-0324-MSchema-wKg-Instruction: using `FULL_SCHEMA_TEMPLATE`
  4.  DeepSeek-V3-0324-DDLSchemaLinks-wKg-Instruction: using DeepSeek-V3-0324 to implement schema-linking
  5.  XiYanSQL-QwenCoder-32B-2504_SC-16g: self-consistency, candidate nums 16
  6.  XiYanSQL-QwenCoder-32B-2504_CSC-SQL_16g8m: generate nums 16, merge nums 8
  
### Analysis
In this section, I demonstrate the approaches I have undertaken and provide some in-depth analysis of their respective outcomes.
#### Pre-processing
#### (1) CoT
Only zero-shot CoT was employed, with the instruction "think step by step" appended to the user prompt. Across all comparisons, zero-shot CoT degraded the EX performance: the DeepSeek baseline dropped by 6.4% relative to its non-CoT version, and XiYanSQL declined by 2.8%. 
#### (2) Schema representation
The XiYanSQL technical report indicates that the choice of schema representation influences end-to-end SQL generation performance. My empirical results corroborate this finding: for non-SFT model, the effect is pronounced, with DDLSchema achieving 55.08% accuracy versus 57.69% for MSchema when calling the DeepSeek API. In contrast, the improvement becomes negligible after SFT, yielding 66.30% and 66.63% for DDLSchema and MSchema, respectively (It is noteworthy that this marginal performance gain is likely due to XiYanSQL having been pre-trained on MSchema representations).
#### (3) Schema linking
While prior studies have consistently reported that schema linking enahnces execution accuracy by supplying the most relevant information to the model, other works have conversely demonstrated that the long context windows benefit the generation of execuable SQL queries. Following DIN-SQL, I employed DeepSeek to implemnet schema linking. However, incorporating these schema links into SQL generation induced a noticeable performance degradation. A comparative accuracy of 41.72% versus 48.63% was observed.
#### Post-processing
#### (1) Self-Consistency
I adopted the majority voting approach for self-consistency: multiple candidate SQL queries were generated and then grouped according to their execution results. Subsequently, the query belonging to the largest group was selected as the final answer. As shown in Table, this strategy yielded a 1.37% improvement in EX (increase from  66.62% to 67.99%).
#### (2) CSC-SQL
CSC-SQL can be deemed as an advanced variant of self-consistency that replaces majority voting with a top-k grouping scheme. This method has demonstrated powerful capability of enhancing the generation of correct queries. The empirical results demonstrate its efficacy: EX rises from 66.62% to 70.73%.

Generating multiple candidate queries increases the likelihood of obtaining a correct answer. When only a single query is produced,  EX is 66.62%; it rises to 80.12% when 16 candidates are generated and to 83.90% with 64 candidates, where the correctness is assumed if at least one query in the candidates is correct.





