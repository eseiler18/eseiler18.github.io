// 1-page CV for research internship applications (the only PDF CV).
// Build: npm run cv   (reads dist/cv/data.json produced by the website build)
#import "template.typ": *

#let data = json(sys.inputs.at("data", default: "/dist/cv/data.json"))
#let phone = sys.inputs.at("phone", default: none)
#let keep(list) = list.filter(e => e.at("resume", default: true))

#show: setup
#set document(title: "Emilien Seiler — Resume")
#header(data, phone: phone)
#summary(data)

#section("Education")
#entries(keep(data.cv.education), short: true)

#section("Publications")
#for p in data.publications.filter(p => p.featured) { publication(p, max: 5) }
#note[Full list: #link(data.site + "/publications", data.site.replace("https://", "") + "/publications")]

#section("Experience")
#entries(newest-first(keep(data.cv.experience)), short: true)

// Awards / mentoring / teaching appear only if some entries are not `resume: false`.
#let others = keep(data.cv.at("awards", default: ())) + keep(data.cv.at("mentoring", default: ())) + keep(data.cv.at("teaching", default: ()))
#if others.len() > 0 {
  section("Awards, Mentoring & Teaching")
  entries(others, short: true)
}

#section("Skills")
#skills(data.cv.skills)
