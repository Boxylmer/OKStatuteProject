import unittest
# statutetext




class TestStatute

test_texts = ['A. There is hereby created the Sexual Assault Forensic Evidence (SAFE) Board within the Office of the Attorney General. The Board shall have the power and duty to:', '1. Examine the process for gathering and analyzing sexual assault forensic evidence kits in this state and work with members of the Legislature to draft proposed legislation to improve the response of medical and law enforcement systems to sexual assault;', '2. Develop a plan for the prioritization and acceptance of untested sexual assault forensic evidence kits identified in the statewide audit conducted by the Board;', '3. Identify possible procedures for the testing of anonymous sexual assault evidence kits;', '4. Identify possible improvements for victim access to evidence other than sexual assault forensic evidence kits including, but not limited to, police reports and other physical evidence;', '5. Identify additional rights of victims concerning the sexual assault forensic evidence kits testing process;', '6. Identify and pursue grants and other funding sources to address untested sexual assault forensic evidence kits, reduce testing wait times, provide victim notification, and improve efficiencies in the kit testing process; and', '7. Develop a comprehensive training plan for equipping and enhancing the work of law enforcement, prosecutors, victim advocates, Sexual Assault Nurse Examiners, and multidisciplinary Sexual Assault Response Teams (SARTs) across all jurisdictions within this state.', 'B. In carrying out its duties and responsibilities, the Board shall:', '1. Promulgate rules establishing criteria for the collection of sexual assault forensic evidence subject to specific, in-depth review by the Board;', '2. Establish and maintain statistical information related to sexual assault forensic evidence collection including, but not limited to, demographic and medical diagnostic information;', '3. Establish procedures for obtaining initial information regarding the collection of sexual assault forensic evidence from medical and law enforcement entities;', '4. Review the policies, practices, and procedures of the medical and law enforcement systems and make specific recommendations to the entities comprising the medical and law enforcement systems for actions necessary to improve such systems;', '5. Review the extent to which the medical and law enforcement systems are coordinated and evaluate whether the state is efficiently discharging its sexual assault forensic evidence collection responsibilities;', '6. Request and obtain a copy of all records and reports pertaining to sexual assault forensic evidence including, but not limited to:', 'a. hospital records,', 'b. court records,', 'c. local, state, and federal law enforcement records,', 'd. medical and dental records, and', 'e. emergency medical service records.', 'Confidential information provided to the Board shall be maintained by the Board in a confidential manner as otherwise required by state and federal law. Any person damaged by disclosure of such confidential information by the Board or its members which is not authorized by law may maintain an action for damages, costs, and attorney fees pursuant to The Governmental Tort Claims Act;', '7. Maintain all confidential information, documents, and records in possession of the Board as confidential and not subject to subpoena or discovery in any civil or criminal proceedings; provided, however, such information, documents, and records otherwise available from other sources shall not be exempt from subpoena or discovery through such sources solely because such information, documents, and records were presented to or reviewed by the Board; and', '8. Exercise all incidental powers necessary and proper for the implementation and administration of the Sexual Assault Forensic Evidence (SAFE) Board.', 'C. The review and discussion of individual cases of sexual assault evidence collection shall be conducted in executive session. All discussions of individual cases and any writings produced by or created for the Board in the course of determining a remedial measure to be recommended by the Board, as the result of a review of an individual case of sexual assault evidence collection, shall be privileged and shall not be admissible in evidence in any proceeding. All other business shall be conducted in accordance with the provisions of the Oklahoma Open Meeting Act. The Board shall periodically conduct meetings to discuss organization and business matters and any actions or recommendations aimed at improvement of the collection of sexual assault forensic evidence which shall be subject to the Oklahoma Open Meeting Act.', 'D. The Board shall submit an annual statistical report on the incidence of sexual assault forensic evidence collection in this state for which the Board has completed its review during the past calendar year including its recommendations, if any, to medical and law enforcement systems. The Board shall also prepare and make available to the public an annual report containing a summary of the activities of the Board relating to the review of sexual assault forensic evidence collection and an evaluation of whether the state is efficiently discharging its sexual assault forensic evidence collection responsibilities. The report shall be completed no later than February 1 of the subsequent year.']
st = StatuteText(test_texts)
st.as_dict()
st.get_text()
js = st.as_json()
new_st = StatuteText.from_json(js)
new_st.as_dict()
str(new_st.as_dict()) == str(st.as_dict())

st.subsections()
st.get_subsection("B.3")
st.get_subsection("B.6.c")
st.get_subsection("A")

st.get_text('')

test_text_first_second_etc = ['Appeals may be allowed as in civil cases, but the possession of monies, funds, properties or assets being so unlawfully used shall be prima facie evidence that it is the properties, funds, monies or assets of the person so using it. Where said monies, funds, properties or assets are sold or otherwise ordered forfeited under the provisions of this act the proceeds shall be disbursed and applied as follows:', 'First. To the payment of the costs of the forfeiting proceedings and actual expenses of preserving the properties.', 'Second. One-eighth (1/8) of the proceeds remaining to the public official, witness, juror or other person to whom the bribe was given, provided such public official, witness, juror or other person had theretofore voluntarily surrendered the same to the sheriff of the county and informed the proper officials of the bribery or attempted bribery.', 'Third. One-eighth (1/8) to the district attorney prosecuting the case.', 'Fourth. The balance to the county treasurer to be credited by him to the court fund of the county.']
st = StatuteText(test_text_first_second_etc)
st.subsections()
st.get_text()
st.as_dict()
st.as_json()
st.get_text(st.subsections()[1])





# StatuteData

def run_example(link: str):
    statute = StatuteData.from_oscn(link)
    return statute.raw_text


subsections = get_statute_title_section_links(STATUTE_21_URL)

# easy case, 301
example_link = print(
    run_example(
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=69082"
    )
)

# 143 contains a nested list
print(
    run_example(
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=496306"
    )
)

# 355 contains historical data at the end
print(
    run_example(
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=69118"
    )
)

# 385 has a break where it should be a continuation
print(
    run_example(
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=69138"
    )
)

# 405 literally says "first, second, third, fourth"
print(
    run_example(
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=69150"
    )
)

# 465 contains weird \xa0 characters
print(
    run_example(
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=487695"
    )
)

# 484.1 contains sections that should be cut off (Historical Data Laws 2009 instead of historical data)
print(
    run_example(
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=455104"
    )
)

# 498 / 499 contain numebrs in (1), (2), format
print(
    run_example(
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=69195"
    )
)

for i, subsection in enumerate(subsections):
    print(subsection["citation"])
    html = requests.get(subsection["link"]).text
    statute = StatuteData.from_html(html)
    print(f"Title: {statute.title}")
    print(f"Section: {statute.section}")
    print(f"Body: {statute.formatted_text()}")

    print("---------------------------------------------")


# TODO: Looks like 385 is a mistake on the websites part (like a lot of others), we can't bank on those mistakes ever really working. 
# So instead, it's probably best to just assume any non-pattern bullet is just a complete side-note and move it to the end at the root level. 


