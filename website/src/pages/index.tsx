import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import styles from './index.module.css';

type LinkTo = {to: string; label: string};

const ticker: {label: string; value: string}[] = [
  {label: 'Stages per request', value: '6'},
  {label: 'Helpers on the team', value: '5'},
  {label: 'Release channels', value: '3'},
  {label: 'Price to use it', value: 'Free'},
];

const sections: LinkTo[] = [
  {to: '/docs/intro', label: 'Introduction'},
  {to: '/docs/get-started', label: 'Get started'},
  {to: '/docs/how-it-works', label: 'How it works'},
  {to: '/docs/guides', label: 'Guides'},
  {to: '/docs/technical', label: 'For technical users'},
  {to: '/docs/faq', label: 'FAQ'},
];

const shorts: {lead: string; tail: string; body: string; link: LinkTo}[] = [
  {
    lead: 'It plans',
    tail: 'before it works',
    body: 'For anything bigger than a quick fix, Agentville talks the request through with you and writes a short plan before it changes anything.',
    link: {to: '/docs/how-it-works', label: 'How it works'},
  },
  {
    lead: 'It tells you',
    tail: 'what is left',
    body: 'Every request ends with a plain report: what was done, what was checked and any decision that is still yours.',
    link: {to: '/docs/guides/following-along', label: 'Follow along'},
  },
];

const guides: {lead: string; tail: string; kicker: string; to: string}[] = [
  {lead: 'Write a', tail: 'good request', kicker: 'Guide', to: '/docs/guides/good-requests'},
  {lead: 'Follow along and', tail: 'make decisions', kicker: 'Guide', to: '/docs/guides/following-along'},
  {lead: 'Keep Agentville', tail: 'up to date', kicker: 'Guide', to: '/docs/guides/updating'},
];

const stages: {number: string; name: string; headline: string; line: string}[] = [
  {
    number: '01',
    name: 'Discuss',
    headline: 'Claude talks the request through with you',
    line: 'What is in, what is out and what "done" looks like. Nothing is changed yet.',
  },
  {
    number: '02',
    name: 'Plan',
    headline: 'A short plan with a check for every task',
    line: 'Claude shows you a summary and carries on; it does not wait for approval.',
  },
  {
    number: '03',
    name: 'Execute',
    headline: 'A helper does each task in the plan',
    line: 'Claude does not ask questions from here on.',
  },
  {
    number: '04',
    name: 'Validate',
    headline: 'A different helper checks each task',
    line: 'It keeps the evidence and never changes the work itself.',
  },
  {
    number: '05',
    name: 'Review',
    headline: 'Another helper reads the work against the plan',
    line: 'It approves the work or asks for changes.',
  },
  {
    number: '06',
    name: 'Report',
    headline: 'Claude tells you what was done',
    line: 'What was checked, and anything still open for you to decide.',
  },
];

const steps: {number: string; tint: string; name: string; tail: string; body: string}[] = [
  {
    number: '01',
    tint: styles.tintPink,
    name: 'Add the plugin',
    tail: 'once',
    body: 'Add Agentville once, from the plugin settings in Claude.',
  },
  {
    number: '02',
    tint: styles.tintSky,
    name: 'Paste two lines',
    tail: 'into settings',
    body: 'Paste two lines into your Claude settings, so every chat uses it.',
  },
  {
    number: '03',
    tint: styles.tintMint,
    name: 'Talk to Claude',
    tail: 'as always',
    body: 'Then talk to Claude as you always do.',
  },
];

function Arrow(): ReactNode {
  return <span aria-hidden="true">{' '}⟶</span>;
}

export default function Home(): ReactNode {
  return (
    <Layout
      title="Home"
      description="Agentville gives Claude a small team of helpers that plan, do, check and report your work.">
      <main className={styles.page}>
        <header className={styles.masthead}>
          <div className={styles.brand}>
            <div className={styles.badge} aria-hidden="true">
              <span className={styles.badgeSmall}>Est · 2026</span>
              <span className={styles.badgeBig}>AV</span>
              <span className={styles.badgeSmall}>Plugin</span>
            </div>
            <div>
              <p className={styles.brandName}>A plugin for Claude</p>
              <p className={styles.brandLine}>Plans · Checks · Reports</p>
              <p className={styles.brandWhere}>Claude Chat · Cowork · Claude Code</p>
            </div>
          </div>
          <div className={styles.nameplate}>
            <Heading as="h1" className={styles.title}>
              Agentville
            </Heading>
            <p className={styles.dateline}>
              <span className={styles.doubleRule} aria-hidden="true" />
              First edition, 2026
              <span className={styles.doubleRule} aria-hidden="true" />
            </p>
          </div>
          <div className={styles.price}>
            <p className={styles.priceSmall}>Open source</p>
            <p className={styles.priceLine}>
              <span className={styles.priceBig}>Price: Free</span>
              <span className={styles.priceNote}>MIT licence</span>
            </p>
          </div>
        </header>

        <div className={styles.tickerFrame}>
          <ul className={styles.ticker} aria-label="Agentville at a glance">
            {ticker.map((item) => (
              <li key={item.label}>
                <span>{item.label}</span>
                <span className={styles.chip}>{item.value}</span>
              </li>
            ))}
          </ul>
        </div>

        <nav className={styles.sections} aria-label="Sections">
          <span className={styles.sectionsCurrent} aria-current="page">
            Front page
          </span>
          {sections.map((item) => (
            <Link key={item.to} to={item.to} className={styles.sectionLink}>
              {item.label}
            </Link>
          ))}
        </nav>

        <section className={styles.heroFrame} aria-labelledby="lead-headline">
          <div className={styles.hero}>
            <div className={styles.heroRail} aria-hidden="true">
              <span>Front page</span>
            </div>
            <div className={styles.heroCopy}>
              <p className={styles.heroKicker}>Lead story · Agentville for Claude</p>
              <Heading as="h2" id="lead-headline" className={styles.heroHeadline}>
                A small team of helpers for Claude that plans, does, checks and reports your work
              </Heading>
              <p className={styles.heroStandfirst}>
                Agentville is a free add-on, called a plugin, for Claude. You add it once, paste two lines into your
                Claude settings, and then you talk to Claude as you always do.
              </p>
              <Link className={styles.heroButton} to="/docs/get-started">
                Get started
                <Arrow />
              </Link>
            </div>
            <div className={styles.heroSide}>
              <span className={styles.ghost} aria-hidden="true">
                06
              </span>
              <div className={styles.stageCard}>
                <p className={styles.stageCardLabel}>The six stages</p>
                <ol className={styles.stageCardList}>
                  {stages.map((stage) => (
                    <li key={stage.number}>{stage.name}</li>
                  ))}
                </ol>
              </div>
            </div>
          </div>
        </section>

        <div className={styles.front}>
          <article className={styles.lead}>
            <div className={styles.leadTop}>
              <p className={styles.mustRead}>Must read</p>
              <Link to="/docs/intro" className={styles.roundArrow} aria-label="Read the introduction">
                <span aria-hidden="true">⟶</span>
              </Link>
            </div>
            <Heading as="h2" className={styles.leadHeadline}>
              Its work is checked, <span className="pp-accent">not just promised</span>
            </Heading>
            <p className={styles.leadStandfirst}>
              A separate helper checks the result, and another reviews it, so you get evidence rather than a promise.
            </p>
            <p className={styles.leadBody}>
              When you ask for something, Agentville first decides how much care the request needs. A quick question gets a quick answer, with no extra steps. A small, clear task goes
              straight to the work. A large or unclear task starts with a short conversation, so Claude understands
              what you want before it builds anything.
            </p>
            <Link className={styles.readMore} to="/docs/intro">
              What is Agentville?
              <Arrow />
            </Link>
          </article>

          <div className={styles.shorts}>
            {shorts.map((story) => (
              <article key={story.lead} className={styles.short}>
                <Heading as="h3" className={styles.shortTitle}>
                  {story.lead} <span className="pp-accent">{story.tail}</span>
                </Heading>
                <p className={styles.shortBody}>{story.body}</p>
                <Link className={styles.readMore} to={story.link.to}>
                  {story.link.label}
                  <Arrow />
                </Link>
              </article>
            ))}
            <div className={styles.promo}>
              <span className={styles.promoScript} aria-hidden="true">
                Use a
                <br />
                terminal?
              </span>
              <div className={styles.promoText}>
                <span className={styles.promoSmall}>For</span>
                <span className={styles.promoBig}>Technical users</span>
                <Link className={styles.promoLink} to="/docs/technical">
                  Claude Code and the installer
                  <Arrow />
                </Link>
              </div>
            </div>
          </div>

          <aside className={styles.sidebar} aria-labelledby="free-heading">
            <div className={styles.skyBox}>
              <Heading as="h2" id="free-heading" className={styles.skyTitle}>
                Free to use
              </Heading>
              <p className={styles.skyLine}>Released under the MIT licence; the source is on GitHub.</p>
              <Link className={styles.outlineButton} to="https://github.com/minhphamdonhat/Agentville">
                On GitHub
              </Link>
            </div>
            <ul className={styles.dispatches} aria-label="Guides">
              {guides.map((guide) => (
                <li key={guide.to}>
                  <span className={styles.dispatchKicker}>{guide.kicker}</span>
                  <Link to={guide.to} className={styles.dispatchTitle}>
                    {guide.lead} <span className="pp-accent">{guide.tail}</span>
                  </Link>
                </li>
              ))}
            </ul>
            <div className={styles.noteBox}>
              <p className={styles.noteTitle}>Add just one version</p>
              <p className={styles.noteText}>
                Add only <Link to="/docs/get-started">the Stable version</Link>: the three versions clash with each
                other, so add just one.
              </p>
              <p className={styles.script} aria-hidden="true">
                Stable only!
              </p>
            </div>
          </aside>
        </div>

        <section className={styles.archive} aria-labelledby="stages-heading">
          <div className={styles.sectionHead}>
            <Heading as="h2" id="stages-heading" className={styles.sectionTitle}>
              <span className={`${styles.accentStrong} pp-highlight`}>The</span> six stages
            </Heading>
            <span className={styles.sectionNote}>Always in the same order</span>
          </div>
          <ol className={styles.archiveGrid}>
            {stages.map((stage) => (
              <li key={stage.number} className={styles.archiveItem}>
                <span className={styles.archiveNumber} aria-hidden="true">
                  {stage.number}
                </span>
                <div>
                  <p className={styles.archiveKicker}>{stage.name}</p>
                  <Heading as="h3" className={styles.archiveHeadline}>
                    {stage.headline}
                  </Heading>
                  <p className={styles.archiveLine}>{stage.line}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className={styles.stepsSection} aria-labelledby="steps-heading">
          <div className={styles.sectionHead}>
            <Heading as="h2" id="steps-heading" className={styles.sectionTitle}>
              <span className={`${styles.accentStrong} pp-highlight`}>Three</span> steps
            </Heading>
            <Link className={styles.readMore} to="/docs/get-started">
              The full steps
              <Arrow />
            </Link>
          </div>
          <ol className={styles.steps}>
            {steps.map((step) => (
              <li key={step.number} className={styles.step}>
                <div className={`${styles.stepBand} ${step.tint}`} aria-hidden="true">
                  <span>{step.number}</span>
                </div>
                <p className={styles.stepKicker}>Step {step.number}</p>
                <Heading as="h3" className={styles.stepTitle}>
                  {step.name} <span className="pp-accent">{step.tail}</span>
                </Heading>
                <p className={styles.stepBody}>{step.body}</p>
              </li>
            ))}
          </ol>
        </section>

        <div className={styles.folio}>
          <span>Page 1</span>
          <span>Agentville · The front page</span>
          <span>minhphamdonhat.github.io/Agentville</span>
        </div>
      </main>
    </Layout>
  );
}
