Design a modern, premium Client Profile page for DSP-AI-Indicator, a personal finance and investment analysis platform.

The purpose of this page is NOT to collect a long financial-planning questionnaire.

The purpose is to collect a small set of essential financial inputs and use them to calculate and display a proprietary:

“Financial Health Score”

The score ranges from 0 to 1000 and should be presented visually like a CIBIL-style financial health meter, using a large SEMICIRCULAR GAUGE/METER with a needle.

IMPORTANT:
DO NOT use a bar chart for the Financial Health Score.
DO NOT use a normal progress bar.
The primary score visualization must be a clean semicircular gauge/meter.

==================================================
PAGE STRUCTURE
==================================================

Create a desktop-first responsive web page.

Page title:
“Your Financial Profile”

Subtitle:
“Help us understand your current financial health.”

At the top, show a subtle profile completion indicator:
“Profile 65% complete”

Use a clean two-column layout on desktop:

LEFT:
Client information and financial input form.

RIGHT:
Financial Health Score preview / result card.

On mobile, stack the sections vertically.

==================================================
1. CLIENT INFORMATION
==================================================

Create a compact “Personal Information” card.

IMPORTANT:
Some information should already be populated from the user's signup account.

Pre-fill these fields automatically from signup:

• Full Name
• Email Address
• Mobile Number

These fields should appear populated and visually indicate:
“From your account”

Do NOT ask the user to enter information that is already available from signup.

Allow the user to edit information where appropriate.

Additional fields:

• Age
• City
• Occupation
• Number of Dependents

Keep this section compact.

==================================================
2. MONTHLY CASH FLOW
==================================================

Section title:
“Monthly Cash Flow”

Fields:

• Monthly Income
• Monthly Household Expenses
• Monthly EMI / Debt Payments
• Other Monthly Income (optional)

Use clean currency inputs with ₹ formatting.

Add small helper text where useful.

Example:

Monthly Income
₹ 75,000

Monthly Expenses
₹ 32,000

Monthly EMI
₹ 12,000

Do not overwhelm the user with financial terminology.

==================================================
3. SAVINGS & INVESTMENTS
==================================================

Section title:
“Savings & Investments”

Fields:

• Total Savings / Cash
• Total Investments
• Emergency Fund

For Total Investments, allow the user to enter one combined amount rather than asking for detailed stock-by-stock information.

Optional small expandable link:

“Add investment details”

This page should remain simple.

Detailed portfolio analysis will be handled elsewhere in DSP-AI-Indicator.

==================================================
4. DEBT & PROTECTION
==================================================

Section title:
“Debt & Protection”

Fields:

• Total Outstanding Loans
• Credit Card Outstanding
• Health Insurance Coverage
• Life / Term Insurance Coverage

Keep the fields simple.

If the user has no debt, provide an easy:

“No outstanding debt”

option.

==================================================
5. FINANCIAL GOAL
==================================================

Section title:
“Primary Financial Goal”

Use selectable cards rather than a complicated form.

Options:

• Wealth Creation
• Retirement
• Regular Income
• Children's Education
• Home Purchase
• Marriage
• Emergency Fund
• Other

After selecting a goal, optionally ask:

Target Amount
Target Year

Keep this section short.

==================================================
6. FINANCIAL HEALTH SCORE — HERO COMPONENT
==================================================

This is the most important visual element on the page.

Create a large premium card titled:

“Financial Health Score”

Display a large SEMICIRCULAR GAUGE / SPEEDOMETER.

The scale must be:

0 — 1000

Use five clearly differentiated zones:

0–199
VERY POOR

200–399
POOR

400–599
FAIR

600–749
GOOD

750–1000
EXCELLENT

Use a smooth segmented/gradient arc.

Place a needle/pointer over the gauge.

Example current state:

742 / 1000

The needle should point to the corresponding position around the “GOOD” section.

Below the meter:

742
/ 1000

GOOD

“Your financial health is currently good.”

The number should be the strongest visual element.

Do NOT make it look like an actual CIBIL score.

Label it clearly as:

“Financial Health Score”

and optionally include subtle helper text:

“An overall view of your current financial position.”

==================================================
7. SCORE BREAKDOWN
==================================================

Below the main gauge, show a compact breakdown.

Title:

“What influences your score?”

Use 5 small horizontal metric cards or rows:

Income Strength
82 / 100

Savings & Investments
76 / 100

Debt Management
71 / 100

Emergency Protection
68 / 100

Goal Readiness
74 / 100

These are component scores contributing to the overall Financial Health Score.

Keep them visually secondary to the main 0–1000 gauge.

Do not use another large chart.

==================================================
8. FINANCIAL INSIGHT
==================================================

Below the score breakdown, create a subtle insight card.

Example:

“Your financial position is healthy.”

Then:

“Building a stronger emergency fund and improving debt management could further improve your Financial Health Score.”

Use AI-style but trustworthy language.

Avoid making investment recommendations on this page.

==================================================
9. PRIMARY ACTION
==================================================

At the bottom of the form:

Primary CTA:

“Calculate My Financial Health Score”

After calculation, change the CTA to:

“Update Financial Profile”

Secondary action:

“Save & Continue Later”

==================================================
VISUAL STYLE
==================================================

Design language:

• Premium fintech
• Modern
• Clean
• Trustworthy
• Minimal
• Professional
• Easy for small/long-term investors to understand
• Strong visual hierarchy
• Generous whitespace
• Rounded cards
• Subtle shadows
• Excellent typography
• Desktop + mobile responsive

Avoid:

• Clutter
• Excessive gradients
• Complex dashboards
• Excessive charts
• Stock-market trading aesthetics
• Cryptocurrency aesthetics
• Neon colors
• Overly technical financial terminology

The Financial Health Score should feel like a calm financial diagnostic tool rather than a trading dashboard.

==================================================
COLOR DIRECTION
==================================================

Use a sophisticated fintech palette consistent with DSP-AI-Indicator.

Prefer:

Deep navy / dark blue for primary UI
White / very light neutral backgrounds
Subtle blue/indigo accents
Green for positive financial health
Amber for fair/attention states
Red/orange only for poor financial-health zones

The gauge should visually transition:

Very Poor → Poor → Fair → Good → Excellent

Use restrained colors rather than overly bright colors.

==================================================
IMPORTANT UX RULES
==================================================

1. DO NOT ask again for information already available from signup.

2. Clearly mark signup-derived fields with a subtle:
“From your account”
indicator.

3. Keep the number of questions low.

4. Use progressive disclosure where possible.

5. Currency fields must use Indian Rupee formatting.

6. Make optional fields clearly distinguishable.

7. The user should understand why the information is being collected.

8. The Financial Health Score should update dynamically as financial inputs change, where appropriate.

9. The gauge must be a SEMICIRCULAR METER WITH A NEEDLE.

10. DO NOT replace the gauge with a bar graph, donut chart, pie chart, or ordinary progress bar.

11. The score is an internal DSP-AI-Indicator financial-health assessment and must not be visually represented as an official CIBIL score.

12. Make the final design feel production-ready and suitable for a real fintech application.

==================================================
EXAMPLE STATE
==================================================

Use realistic placeholder data to demonstrate the completed state:

Name:
Abhishek Pawar

Email:
abhishek@example.com

Mobile:
+91 XXXXX XXXXX

Age:
28

Occupation:
Salaried

Monthly Income:
₹75,000

Monthly Expenses:
₹32,000

Monthly EMI:
₹12,000

Total Savings:
₹4,50,000

Total Investments:
₹25,00,000

Emergency Fund:
₹2,00,000

Outstanding Loans:
₹8,50,000

Health Insurance:
₹10,00,000

Life Insurance:
₹50,00,000

Primary Goal:
Wealth Creation

Target Year:
2036

Illustrative Financial Health Score:

742 / 1000

GOOD

Important:
Clearly label the example score as illustrative/demo data in the design if necessary.

==================================================
FINAL DESIGN PRIORITY
==================================================

The user should immediately understand:

“My financial health is 742 out of 1000.”

The page should feel simple enough to complete in approximately 2–4 minutes.

The Financial Health Score gauge should be the visual centerpiece of the page.

Create polished desktop and mobile versions with consistent spacing, components, typography, states, input styles, validation states, and responsive behavior.