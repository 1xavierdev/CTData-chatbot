import { Component, output } from '@angular/core';

@Component({
  selector: 'app-home',
  templateUrl: './home.html',
  styleUrl: './home.css',
})
export class Home {
  /** Asks the page to open the chat assistant. */
  readonly askAssistant = output<void>();

  protected readonly stats = [
    { value: '169', label: 'towns covered' },
    { value: '8', label: 'counties' },
    { value: '9', label: 'planning regions' },
    { value: '1,000+', label: 'datasets & indicators' },
  ];

  protected readonly topics = [
    { icon: '🎓', name: 'Education', text: 'Graduation, attendance, test results and attainment.', href: 'https://www.ctdata.org/education', ai: true },
    { icon: '🏥', name: 'Health', text: 'Health outcomes, insurance and access to care.', href: 'https://www.ctdata.org/data-by-topic' },
    { icon: '💼', name: 'Economy & Workforce', text: 'Employment, wages, income and industries.', href: 'https://www.ctdata.org/data-by-topic' },
    { icon: '🏠', name: 'Housing', text: 'Affordability, tenure and housing stock.', href: 'https://www.ctdata.org/data-by-topic' },
    { icon: '👥', name: 'Demographics', text: 'Population, age, race and ethnicity by town.', href: 'https://www.ctdata.org/census' },
    { icon: '🗺️', name: 'Geography', text: 'Maps, boundaries and geospatial tools.', href: 'https://www.ctdata.org/geographic-resources' },
  ];

  // From https://www.ctdata.org/education
  protected readonly datasets = [
    { name: 'Four Year Graduation Rates', group: 'Educational Attainment', by: 'Gender, race/ethnicity, English learner, special education and more', href: 'https://public-edsight.ct.gov/performance/four-year-graduation-rates?language=en_US' },
    { name: 'Chronic Absenteeism', group: 'Student Behavior', by: 'Grade, gender, race/ethnicity, meal eligibility and more', href: 'https://public-edsight.ct.gov/students/chronic-absenteeism?language=en_US' },
    { name: 'Suspension Rates', group: 'Student Behavior', by: 'Grade, gender, race/ethnicity, special education and more', href: 'https://public-edsight.ct.gov/students/suspension-rates?language=en_US' },
    { name: 'Smarter Balanced Performance', group: 'Testing & Evaluation', by: 'Achievement and participation by district and school', href: 'https://public-edsight.ct.gov/performance/smarter-balanced-achievement-participation?language=en_US' },
    { name: 'Educational Attainment', group: 'Educational Attainment', by: 'Interactive map of attainment across Connecticut', href: 'https://experience.arcgis.com/experience/ab81a358575d4633990328e33094dfc6/' },
    { name: 'EDI Early Development Instrument', group: 'Projects by CTData', by: "Children's progress on age-appropriate developmental milestones", href: 'https://edi.ctdata.org/' },
  ];

  protected readonly posts = [
    { date: 'August 31, 2022', title: 'Older Connecticut Residents Have Higher Student Loan Debt', href: 'https://www.ctdata.org/blog/student-debt' },
    { date: 'July 18, 2022', title: "Learn about the Census Bureau's Post-Secondary Employment Outcomes (PSEO) Data", href: 'https://www.ctdata.org/blog/learn-about-the-census-bureaus-post-secondary-employment-outcomes-data' },
    { date: 'August 28, 2019', title: 'Recent Mothers with Higher Education More Likely to Be in the Labor Force', href: 'https://www.ctdata.org/blog/recent-mothers-with-higher-education-more-likely-to-be-in-the-labor-force' },
  ];
}
