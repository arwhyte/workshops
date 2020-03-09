# # Survival analysis of NHANES III data
#
# Data sources:
#
# [NHANES data files](https://wwwn.cdc.gov/nchs/nhanes/nhanes3/datafiles.aspx)
#
# [NHANES mortality files](https://www.cdc.gov/nchs/data-linkage/mortality-public.htm)

import statsmodels.api as sm
import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt

# Read the survival data

fname = "NHANES_III_MORT_2011_PUBLIC.dat.gz"
colspecs = [(0, 5), (14, 15), (15, 16), (43, 46), (46, 49)]
names = ["seqn", "eligstat", "mortstat", "permth_int", "permth_exam"]
f = os.path.join("../data", fname)
surv = pd.read_fwf(f, colspecs=colspecs, names=names, compression="gzip")

# Read the interview/examination data

colspecs = [(0, 5), (14, 15), (17, 19), (28, 31), (33, 34), (32, 33), (34, 35), (35, 41)]
names = ["seqn", "sex", "age", "county", "urbanrural", "state", "region", "poverty"]
f = os.path.join("../data", "adult.dat.gz")
df = pd.read_fwf(f, colspecs=colspecs, names=names, compression="gzip")
df = pd.merge(surv, df, left_on="seqn", right_on="seqn")

# These are variables that may predict mortality.

df["poverty"] = df["poverty"].replace({888888: np.nan})
df["female"] = (df.sex == 2).astype(np.int)
df["rural"] = (df.urbanrural == 2).astype(np.int)

# Calculate the age at death or censoring

df["age_int"] = 12*df.age  # months
df["end"] = df.age_int + df.permth_int  # months

# It is possible to do something more sophisticated about missing data, but here we
# will do a complete case analysis.

df = df.dropna()

# SurvfuncRight can't handle 0 survival times

df = df.loc[df.end > df.age_int]

# The hazard function is the derivative of the cumulative hazard function.
# Here we calculate the derivative numerically using second differences.
# This tends to produce a noisy estimate of the derivative, so we smooth
# it below with local polynomial smoothing.

def hazard(sf):
    tm = s.surv_times
    pr = s.surv_prob
    ii = (pr > 0)
    tm = tm[ii]
    pr = pr[ii]
    lpr = np.log(pr)
    return tm[0:-1], -np.diff(lpr) / np.diff(tm)

# Plot the hazard functions for women and men.  These are unadjusted hazard functions,
# i.e. they describe the hazard for all people at a given age.

plt.grid(True)
sex = {0: "Male", 1: "Female"}
for female in (0, 1):
    ii = df.female == female
    s = sm.SurvfuncRight(df.loc[ii, "end"], df.loc[ii, "mortstat"], entry=df.loc[ii, "age_int"])
    tm, hz = hazard(s)
    ha = sm.nonparametric.lowess(np.log(hz), tm/12)
    plt.plot(ha[:, 0], ha[:, 1], lw=3, label=sex[female])
ha, lb = plt.gca().get_legend_handles_labels()
leg = plt.figlegend(ha, lb, "upper center", ncol=2)
leg.draw_frame(False)
plt.xlabel("Age", size=15)
plt.ylabel("Log hazard", size=15)
_ = plt.xlim(18, 90)

# Fit a proportional hazards regression model, using sex, urbanicity, and
# poverty status to explain the variation in life span.

fml = "end ~ female + rural + C(region) + poverty"
model1 = sm.PHReg.from_formula(fml, status="mortstat", entry=df.age_int,
                               data=df)
result1 = model1.fit()
print(result1.summary())

# Fit the same model as above, not stratifying by state of residence.

fml = "end ~ female + rural + C(region) + poverty"
model2 = sm.PHReg.from_formula(fml, status="mortstat", entry=df.age_int,
                               strata=df.state, data=df)
result2 = model2.fit()
print(result2.summary())

# Now stratify instead on county.  Note that the sex and poverty coefficients
# are similar to what we saw above, but the urbanicity coefficient (rural)
# changes substantially.  Below, we compare people living in rural areas to
# people living in non-rural areas, while living in the same county.  Above,
# we compare people living in rural areas to people living in non-rural areas
# without the requirement that they live in the same county.

fml = "end ~ female + rural + C(region) + poverty"
model3 = sm.PHReg.from_formula(fml, status="mortstat", entry=df.age_int,
                               strata=df.county, data=df)
result3 = model3.fit()
print(result3.summary())
