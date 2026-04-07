import { useEffect, useState, useCallback, useRef } from 'react'
import { Link, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom'
import ticketorbiLogo from './assets/ticketorbi-logo.svg'

const SITE_NAME = 'Ticketorbi'

const listDateFormatter = new Intl.DateTimeFormat('en-PH', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
})

const detailDateFormatter = new Intl.DateTimeFormat('en-PH', {
  month: 'long',
  day: 'numeric',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
})

function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

function buildEventPath(event) {
  return `/events/${event.slug || slugify(event.title)}`
}

function formatPrice(price) {
  if (price === null || price === undefined) {
    return 'TBA'
  }

  return new Intl.NumberFormat('en-PH', {
    style: 'currency',
    currency: 'PHP',
  }).format(price)
}

function getConfirmationStorageKey(bookingReference) {
  return `ticketorbi-order-${bookingReference}`
}

async function requestJson(url, options) {
  const response = await fetch(url, options)
  const payload = await response.json().catch(() => ({}))

  if (!response.ok) {
    const error = new Error(payload.detail || 'Request failed.')
    error.status = response.status
    error.payload = payload
    throw error
  }

  return payload
}

async function fetchEventBySlug(slug) {
  return requestJson(`/api/events/${slug}`)
}

async function fetchAdminEvent(id) {
  return requestJson(`/api/admin/events/${id}`)
}

function getTotalSlots(ticketTypes) {
  return ticketTypes.reduce((sum, ticketType) => sum + (ticketType.total_slots || 0), 0)
}

/* ──────────── Navbar ──────────── */

function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  return (
    <>
      <nav className="navbar">
        <div className="navbar-inner">
          <Link className="navbar-logo" to="/"><img src={ticketorbiLogo} alt={SITE_NAME} /></Link>
          <div className="navbar-links">
            <Link to="/" className={location.pathname === '/' ? 'active' : ''}>Home</Link>
            <Link to="/events" className={location.pathname === '/events' ? 'active' : ''}>Events</Link>
            <Link to="/classes" className={location.pathname === '/classes' ? 'active' : ''}>Classes</Link>
          </div>
          <button
            className="navbar-hamburger"
            onClick={() => setMenuOpen(true)}
            aria-label="Open menu"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
        </div>
      </nav>
      <div className={`mobile-menu ${menuOpen ? 'open' : ''}`} onClick={() => setMenuOpen(false)}>
        <div className="mobile-menu-panel" onClick={(e) => e.stopPropagation()}>
          <button className="mobile-menu-close" onClick={() => setMenuOpen(false)} aria-label="Close menu">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
          <Link to="/">Home</Link>
          <Link to="/events">Events</Link>
          <Link to="/classes">Classes</Link>
        </div>
      </div>
    </>
  )
}

/* ──────────── Footer ──────────── */

function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <p className="footer-copy">&copy; {new Date().getFullYear()} {SITE_NAME}. All rights reserved.</p>
        <div className="footer-social">
          <a href="https://facebook.com" target="_blank" rel="noopener noreferrer" aria-label="Facebook">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/>
            </svg>
          </a>
          <a href="https://instagram.com" target="_blank" rel="noopener noreferrer" aria-label="Instagram">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
              <circle cx="12" cy="12" r="4"/>
              <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/>
            </svg>
          </a>
        </div>
      </div>
    </footer>
  )
}

/* ──────────── Carousel ──────────── */

function Carousel({ events }) {
  const [current, setCurrent] = useState(0)
  const timerRef = useRef(null)

  const startTimer = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = setInterval(() => {
      setCurrent((prev) => (prev + 1) % events.length)
    }, 5000)
  }, [events.length])

  useEffect(() => {
    if (events.length <= 1) return
    startTimer()
    return () => clearInterval(timerRef.current)
  }, [events.length, startTimer])

  function goTo(index) {
    setCurrent(index)
    startTimer()
  }

  function prev() {
    goTo((current - 1 + events.length) % events.length)
  }

  function next() {
    goTo((current + 1) % events.length)
  }

  if (events.length === 0) return null

  return (
    <section className="carousel-section">
      <div className="carousel-wrapper">
        <div className="carousel-track">
          {events.map((event, i) => {
            const prevIdx = (current - 1 + events.length) % events.length
            const nextIdx = (current + 1) % events.length
            const slideClass = i === current ? 'active' : i === prevIdx ? 'prev' : i === nextIdx ? 'next' : ''
            return (
            <Link
              key={event.id}
              to={buildEventPath(event)}
              className={`carousel-slide ${slideClass}`}
            >
              <img src={event.poster_url} alt={event.title} />
              <div className="carousel-overlay">
                <h2>{event.title}</h2>
                <p>{listDateFormatter.format(new Date(event.event_date))} &middot; {event.venue_name}</p>
                {event.ticket_price != null && (
                  <span className="carousel-price">Starts at {formatPrice(event.ticket_price)}</span>
                )}
              </div>
            </Link>
            )
          })}
          {events.length > 1 && (
            <>
              <button className="carousel-nav prev" onClick={(e) => { e.preventDefault(); prev() }} aria-label="Previous">&#8249;</button>
              <button className="carousel-nav next" onClick={(e) => { e.preventDefault(); next() }} aria-label="Next">&#8250;</button>
            </>
          )}
        </div>
        {events.length > 1 && (
          <div className="carousel-dots">
            {events.map((_, i) => (
              <button
                key={i}
                className={`carousel-dot ${i === current ? 'active' : ''}`}
                onClick={() => goTo(i)}
                aria-label={`Go to slide ${i + 1}`}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

/* ──────────── Compact Card ──────────── */

function CompactCard({ event }) {
  return (
    <Link className="compact-card" to={buildEventPath(event)}>
      <img className="compact-card-image" src={event.poster_url} alt={event.title} />
      <div className="compact-card-body">
        <h3 className="compact-card-title">{event.title}</h3>
        <p className="compact-card-date">{listDateFormatter.format(new Date(event.event_date))}</p>
        {event.ticket_price != null && (
          <p className="compact-card-price">Starts at {formatPrice(event.ticket_price)}</p>
        )}
      </div>
    </Link>
  )
}

/* ──────────── Home Page ──────────── */

function HomePage() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadEvents() {
      try {
        setEvents(await requestJson('/api/events'))
      } catch {
        // silent
      } finally {
        setLoading(false)
      }
    }
    loadEvents()
  }, [])

  const displayEvents = events.slice(0, 4)

  return (
    <>
      {!loading && events.length > 0 && <Carousel events={events.slice(0, 5)} />}

      {/* Events Section */}
      <div className="section-shell section-purple">
        <div className="section-inner">
          <div className="section-header">
            <h2>Events</h2>
            <Link className="see-more-link" to="/events">See more &rarr;</Link>
          </div>
          {loading && <p style={{ color: 'rgba(255,255,255,0.7)' }}>Loading...</p>}
          {!loading && displayEvents.length > 0 && (
            <div className="compact-grid">
              {displayEvents.map((event) => (
                <CompactCard key={event.id} event={event} />
              ))}
            </div>
          )}
          {!loading && displayEvents.length === 0 && (
            <p style={{ color: 'rgba(255,255,255,0.7)' }}>No events available right now.</p>
          )}
        </div>
      </div>

      {/* Classes Section */}
      <div className="section-shell section-white">
        <div className="section-inner">
          <div className="section-header">
            <h2>Classes</h2>
            <Link className="see-more-link" to="/classes">See more &rarr;</Link>
          </div>
          <p style={{ color: 'var(--gray-500)' }}>Classes coming soon. Stay tuned!</p>
        </div>
      </div>

      {/* CTA Section */}
      <div className="cta-section">
        <h2>Want to put your event or class?</h2>
        <p>Let&rsquo;s connect and get your event listed on {SITE_NAME}.</p>
        <a
          className="cta-button"
          href="mailto:hello@ticketorbi.com"
        >
          Get in Touch
        </a>
      </div>

      <Footer />
    </>
  )
}

/* ──────────── Events List Page ──────────── */

function EventListPage() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadEvents() {
      try {
        setEvents(await requestJson('/api/events'))
      } catch (loadError) {
        setError(loadError.message)
      } finally {
        setLoading(false)
      }
    }

    loadEvents()
  }, [])

  return (
    <main className="page-shell">
      <header className="page-header">
        <h1>All Events</h1>
        <p>Browse upcoming performances and live experiences.</p>
      </header>

      {loading && <p className="status-message">Loading events...</p>}
      {error && <p className="status-message">{error}</p>}
      {!loading && !error && events.length === 0 && (
        <p className="status-message">No published events are available right now.</p>
      )}

      {!loading && !error && events.length > 0 && (
        <section className="event-grid">
          {events.map((event) => (
            <Link className="event-card" key={event.id} to={buildEventPath(event)}>
              <img className="event-card-image" src={event.poster_url} alt={event.title} />
              <div className="event-card-content">
                <div className="event-card-head">
                  <h2>{event.title}</h2>
                  <span className={`badge ${event.total_slots > 0 ? 'available' : 'sold-out'}`}>
                    {event.total_slots > 0 ? 'Available' : 'Sold Out'}
                  </span>
                </div>
                <p className="event-date">{listDateFormatter.format(new Date(event.event_date))}</p>
                <p className="event-meta">{event.venue_name}</p>
                <p className="event-price">From {formatPrice(event.ticket_price)}</p>
              </div>
            </Link>
          ))}
        </section>
      )}

      <Footer />
    </main>
  )
}

/* ──────────── Classes Page (placeholder) ──────────── */

function ClassesPage() {
  return (
    <main className="page-shell">
      <header className="page-header">
        <h1>Classes</h1>
        <p>Discover workshops, masterclasses, and learning experiences.</p>
      </header>
      <p className="status-message">Classes coming soon. Stay tuned!</p>
      <Footer />
    </main>
  )
}

/* ──────────── Event Detail Page ──────────── */

function EventDetailPage() {
  const { slug } = useParams()
  const navigate = useNavigate()
  const [event, setEvent] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadEvent() {
      if (!slug) {
        setNotFound(true)
        setLoading(false)
        return
      }

      try {
        setEvent(await fetchEventBySlug(slug))
      } catch (loadError) {
        if (loadError.status === 404) {
          setNotFound(true)
        } else {
          setError(loadError.message)
        }
      } finally {
        setLoading(false)
      }
    }

    loadEvent()
  }, [slug])

  if (loading) {
    return (
      <main className="page-shell">
        <p className="status-message">Loading event...</p>
      </main>
    )
  }

  if (notFound) {
    return (
      <main className="page-shell detail-page">
        <Link className="back-link" to="/">
          &larr; Back to events
        </Link>
        <p className="status-message">This event could not be found.</p>
      </main>
    )
  }

  if (error) {
    return (
      <main className="page-shell detail-page">
        <Link className="back-link" to="/">
          &larr; Back to events
        </Link>
        <p className="status-message">{error}</p>
      </main>
    )
  }

  const availableSlots = getTotalSlots(event.ticket_types || [])

  return (
    <main className="page-shell detail-page">
      <Link className="back-link" to="/">
        &larr; Back to events
      </Link>

      <section className="detail-layout">
        <img className="detail-image" src={event.poster_url} alt={event.title} />

        <div className="detail-content">
          <p className="eyebrow">Event Details</p>
          <h1>{event.title}</h1>
          <p className="detail-date">{detailDateFormatter.format(new Date(event.event_date))}</p>

          <div className="detail-block">
            <h2>Venue</h2>
            <p>{event.venue_name}</p>
            <p>{event.venue_address}</p>
          </div>

          <div className="detail-block">
            <h2>Description</h2>
            <p>{event.description}</p>
          </div>

          <div className="detail-block">
            <h2>Ticket Types</h2>
            <div className="ticket-type-list">
              {(event.ticket_types || []).map((ticketType) => (
                <div className="ticket-type-row" key={ticketType.id}>
                  <div>
                    <strong>{ticketType.name}</strong>
                  </div>
                  <div>{formatPrice(ticketType.price)}</div>
                  <div>{ticketType.total_slots} slots available</div>
                </div>
              ))}
            </div>
          </div>

          {availableSlots > 0 ? (
            <button
              className="buy-button"
              type="button"
              onClick={() => navigate(`/events/${event.slug}/checkout`)}
            >
              Buy Tickets
            </button>
          ) : (
            <p className="sold-out-text">Sold Out</p>
          )}
        </div>
      </section>
    </main>
  )
}

/* ──────────── Checkout Page ──────────── */

function CheckoutPage() {
  const { slug } = useParams()
  const navigate = useNavigate()
  const [event, setEvent] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [formValues, setFormValues] = useState({
    buyer_name: '',
    buyer_email: '',
    quantity: '1',
    ticket_type_id: '',
  })
  const [fieldErrors, setFieldErrors] = useState({})

  useEffect(() => {
    async function loadEvent() {
      if (!slug) {
        setNotFound(true)
        setLoading(false)
        return
      }

      try {
        const data = await fetchEventBySlug(slug)
        setEvent(data)
        const availableTicketType = (data.ticket_types || []).find((ticketType) => ticketType.total_slots > 0)
        setFormValues((currentValues) => ({
          ...currentValues,
          ticket_type_id: availableTicketType?.id || '',
        }))
      } catch (loadError) {
        if (loadError.status === 404) {
          setNotFound(true)
        } else {
          setError(loadError.message)
        }
      } finally {
        setLoading(false)
      }
    }

    loadEvent()
  }, [slug])

  function handleChange(changeEvent) {
    const { name, value } = changeEvent.target
    setFormValues((currentValues) => ({
      ...currentValues,
      [name]: value,
    }))
    setFieldErrors((currentErrors) => ({
      ...currentErrors,
      [name]: '',
    }))
    setError('')
  }

  function validateForm() {
    const nextErrors = {}
    const quantity = Number(formValues.quantity)

    if (formValues.buyer_name.trim().length < 2) {
      nextErrors.buyer_name = 'Please enter your full name.'
    }

    if (!formValues.buyer_email.trim()) {
      nextErrors.buyer_email = 'Please enter your email address.'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formValues.buyer_email.trim())) {
      nextErrors.buyer_email = 'Please enter a valid email address.'
    }

    if (!formValues.ticket_type_id) {
      nextErrors.ticket_type_id = 'Please select a ticket type.'
    }

    if (!Number.isInteger(quantity) || quantity < 1 || quantity > 10) {
      nextErrors.quantity = 'Please choose between 1 and 10 tickets.'
    }

    setFieldErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }

  async function handleSubmit(submitEvent) {
    submitEvent.preventDefault()

    if (!event || !validateForm()) {
      return
    }

    setSubmitting(true)
    setError('')

    try {
      const payload = await requestJson('/api/orders', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          event_id: event.id,
          ticket_type_id: formValues.ticket_type_id,
          buyer_name: formValues.buyer_name.trim(),
          buyer_email: formValues.buyer_email.trim(),
          quantity: Number(formValues.quantity),
        }),
      })

      const selectedTicketType =
        (event.ticket_types || []).find((ticketType) => ticketType.id === formValues.ticket_type_id) || null

      const confirmation = {
        booking_reference: payload.booking_reference,
        buyer_name: payload.buyer_name,
        buyer_email: payload.buyer_email,
        quantity: payload.quantity,
        total_amount: payload.total_amount,
        status: payload.status,
        ticket_type_name: payload.ticket_type_name || selectedTicketType?.name || '',
        event: {
          title: event.title,
          slug: event.slug,
          date: event.event_date,
          venue_name: event.venue_name,
        },
      }

      sessionStorage.setItem(
        getConfirmationStorageKey(payload.booking_reference),
        JSON.stringify(confirmation),
      )

      navigate(`/orders/${payload.booking_reference}/confirmation`, {
        state: confirmation,
      })
    } catch (submitError) {
      if (submitError.status === 404) {
        setNotFound(true)
      } else {
        setError(submitError.message)
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <main className="page-shell">
        <p className="status-message">Loading checkout...</p>
      </main>
    )
  }

  if (notFound) {
    return (
      <main className="page-shell detail-page">
        <p className="status-message">This event could not be found.</p>
      </main>
    )
  }

  if (error && !event) {
    return (
      <main className="page-shell detail-page">
        <p className="status-message">{error}</p>
      </main>
    )
  }

  const selectedTicketType =
    (event.ticket_types || []).find((ticketType) => ticketType.id === formValues.ticket_type_id) || null
  const quantity = Number(formValues.quantity) || 0
  const totalAmount = (selectedTicketType?.price || 0) * quantity

  return (
    <main className="page-shell checkout-page">
      <Link className="back-link" to={`/events/${slug}`}>
        &larr; Back to event
      </Link>
      <section className="checkout-layout">
        <div className="checkout-summary">
          <p className="eyebrow">Order Summary</p>
          <h1 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700 }}>{event.title}</h1>
          <p className="detail-date">{detailDateFormatter.format(new Date(event.event_date))}</p>
          <p className="event-meta">{event.venue_name}</p>
          {selectedTicketType && (
            <p className="event-meta">
              {selectedTicketType.name} &middot; {formatPrice(selectedTicketType.price)} per ticket
            </p>
          )}
        </div>

        <form className="checkout-form" onSubmit={handleSubmit}>
          <label className="form-field">
            <span>Ticket Type</span>
            <select name="ticket_type_id" value={formValues.ticket_type_id} onChange={handleChange} required>
              <option value="">Select ticket type</option>
              {(event.ticket_types || []).map((ticketType) => (
                <option
                  key={ticketType.id}
                  value={ticketType.id}
                  disabled={ticketType.total_slots === 0}
                >
                  {ticketType.name} &middot; {formatPrice(ticketType.price)} &middot; {ticketType.total_slots} slots
                </option>
              ))}
            </select>
            {fieldErrors.ticket_type_id && (
              <small className="field-error">{fieldErrors.ticket_type_id}</small>
            )}
          </label>

          <label className="form-field">
            <span>Full Name</span>
            <input
              name="buyer_name"
              type="text"
              value={formValues.buyer_name}
              onChange={handleChange}
              required
            />
            {fieldErrors.buyer_name && <small className="field-error">{fieldErrors.buyer_name}</small>}
          </label>

          <label className="form-field">
            <span>Email Address</span>
            <input
              name="buyer_email"
              type="email"
              value={formValues.buyer_email}
              onChange={handleChange}
              required
            />
            {fieldErrors.buyer_email && (
              <small className="field-error">{fieldErrors.buyer_email}</small>
            )}
          </label>

          <label className="form-field">
            <span>Number of Tickets</span>
            <input
              name="quantity"
              type="number"
              min="1"
              max="10"
              value={formValues.quantity}
              onChange={handleChange}
              required
            />
            {fieldErrors.quantity && <small className="field-error">{fieldErrors.quantity}</small>}
          </label>

          <div className="running-total">
            <span>Running Total</span>
            <strong>{formatPrice(totalAmount)}</strong>
          </div>

          {error && <p className="status-message form-message">{error}</p>}

          <button className="buy-button" type="submit" disabled={submitting}>
            {submitting ? 'Confirming...' : 'Confirm Order'}
          </button>
        </form>
      </section>
    </main>
  )
}

/* ──────────── Order Confirmation Page ──────────── */

function OrderConfirmationPage() {
  const { booking_reference: bookingReference } = useParams()
  const location = useLocation()
  const [confirmation, setConfirmation] = useState(location.state || null)

  useEffect(() => {
    if (location.state || !bookingReference) {
      return
    }

    const savedConfirmation = sessionStorage.getItem(getConfirmationStorageKey(bookingReference))
    if (savedConfirmation) {
      setConfirmation(JSON.parse(savedConfirmation))
    }
  }, [bookingReference, location.state])

  if (!confirmation) {
    return (
      <main className="page-shell confirmation-page">
        <p className="status-message">Order details are unavailable.</p>
      </main>
    )
  }

  return (
    <main className="page-shell confirmation-page">
      <section className="confirmation-card">
        <p className="eyebrow">Order Confirmed</p>
        <h1 style={{ margin: 0, fontSize: '1.6rem', fontWeight: 700 }}>Thank You!</h1>
        <p className="confirmation-reference">{confirmation.booking_reference}</p>

        <div className="confirmation-grid">
          <div>
            <span className="summary-label">Event</span>
            <strong>{confirmation.event.title}</strong>
          </div>
          <div>
            <span className="summary-label">Date</span>
            <strong>{detailDateFormatter.format(new Date(confirmation.event.date))}</strong>
          </div>
          <div>
            <span className="summary-label">Venue</span>
            <strong>{confirmation.event.venue_name}</strong>
          </div>
          <div>
            <span className="summary-label">Ticket Type</span>
            <strong>{confirmation.ticket_type_name}</strong>
          </div>
          <div>
            <span className="summary-label">Buyer Name</span>
            <strong>{confirmation.buyer_name}</strong>
          </div>
          <div>
            <span className="summary-label">Email</span>
            <strong>{confirmation.buyer_email}</strong>
          </div>
          <div>
            <span className="summary-label">Quantity</span>
            <strong>{confirmation.quantity}</strong>
          </div>
          <div>
            <span className="summary-label">Total Amount</span>
            <strong>{formatPrice(confirmation.total_amount)}</strong>
          </div>
        </div>

        <p className="confirmation-note">Your eTicket will be sent to your email shortly.</p>
        {confirmation.event.slug && (
          <Link className="confirmation-link" to={`/events/${confirmation.event.slug}`}>
            &larr; Back to event page
          </Link>
        )}
      </section>
    </main>
  )
}

/* ──────────── Admin: Event List ──────────── */

function AdminEventListPage() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadEvents() {
      try {
        setEvents(await requestJson('/api/admin/events'))
      } catch (loadError) {
        setError(loadError.message)
      } finally {
        setLoading(false)
      }
    }

    loadEvents()
  }, [])

  return (
    <main className="page-shell admin-page">
      <div className="admin-header">
        <div>
          <p className="eyebrow">Admin</p>
          <h1>Events</h1>
        </div>
        <Link className="admin-button" to="/admin/events/new">
          + Create Event
        </Link>
      </div>

      {loading && <p className="status-message">Loading events...</p>}
      {error && <p className="status-message">{error}</p>}

      {!loading && !error && (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Date</th>
                <th>Venue</th>
                <th>Status</th>
                <th>Ticket Types</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.id}>
                  <td>{event.title}</td>
                  <td>{detailDateFormatter.format(new Date(event.event_date))}</td>
                  <td>{event.venue_name}</td>
                  <td>
                    <span className={`badge admin-status admin-status-${event.status}`}>{event.status}</span>
                  </td>
                  <td>{event.ticket_type_count}</td>
                  <td className="admin-actions-cell">
                    <Link className="admin-link" to={`/admin/events/${event.id}`}>
                      Edit
                    </Link>
                    <Link className="admin-link" to={`/admin/events/${event.id}`}>
                      View ticket types
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  )
}

/* ──────────── Admin: Event Form ──────────── */

function AdminEventForm({
  mode,
  event,
  formValues,
  setFormValues,
  onSubmit,
  submitting,
  error,
  successMessage,
  posterPreview,
  onPosterSelect,
}) {
  return (
    <form className="admin-form" onSubmit={onSubmit}>
      <label className="form-field">
        <span>Title</span>
        <input
          name="title"
          type="text"
          value={formValues.title}
          onChange={(eventTarget) =>
            setFormValues((currentValues) => ({ ...currentValues, title: eventTarget.target.value }))
          }
          required
        />
      </label>

      <label className="form-field">
        <span>Description</span>
        <textarea
          name="description"
          value={formValues.description}
          onChange={(eventTarget) =>
            setFormValues((currentValues) => ({ ...currentValues, description: eventTarget.target.value }))
          }
          rows="5"
        />
      </label>

      <label className="form-field">
        <span>Event Date + Time</span>
        <input
          name="event_date"
          type="datetime-local"
          value={formValues.event_date}
          onChange={(eventTarget) =>
            setFormValues((currentValues) => ({ ...currentValues, event_date: eventTarget.target.value }))
          }
          required
        />
      </label>

      <label className="form-field">
        <span>Venue Name</span>
        <input
          name="venue_name"
          type="text"
          value={formValues.venue_name}
          onChange={(eventTarget) =>
            setFormValues((currentValues) => ({ ...currentValues, venue_name: eventTarget.target.value }))
          }
          required
        />
      </label>

      <label className="form-field">
        <span>Venue Address</span>
        <input
          name="venue_address"
          type="text"
          value={formValues.venue_address}
          onChange={(eventTarget) =>
            setFormValues((currentValues) => ({ ...currentValues, venue_address: eventTarget.target.value }))
          }
        />
      </label>

      <label className="form-field">
        <span>Producer Name</span>
        <input
          name="producer_name"
          type="text"
          value={formValues.producer_name}
          onChange={(eventTarget) =>
            setFormValues((currentValues) => ({ ...currentValues, producer_name: eventTarget.target.value }))
          }
        />
      </label>

      <label className="form-field">
        <span>Status</span>
        <select
          name="status"
          value={formValues.status}
          onChange={(eventTarget) =>
            setFormValues((currentValues) => ({ ...currentValues, status: eventTarget.target.value }))
          }
        >
          <option value="draft">draft</option>
          <option value="published">published</option>
          <option value="cancelled">cancelled</option>
        </select>
      </label>

      <label className="form-field">
        <span>Poster Upload</span>
        <input type="file" accept="image/*" onChange={onPosterSelect} />
      </label>

      {(posterPreview || event?.poster_url) && (
        <div className="admin-poster-preview">
          <img src={posterPreview || event?.poster_url} alt={formValues.title || 'Poster preview'} />
        </div>
      )}

      {error && <p className="status-message form-message">{error}</p>}
      {successMessage && <p className="success-banner form-success">{successMessage}</p>}

      <button className="admin-button" type="submit" disabled={submitting}>
        {submitting
          ? mode === 'create'
            ? 'Creating...'
            : 'Saving...'
          : mode === 'create'
            ? 'Create Event'
            : 'Save Changes'}
      </button>
    </form>
  )
}

/* ──────────── Admin: Create Event ──────────── */

function toDateTimeLocalString(value) {
  if (!value) {
    return ''
  }

  const date = new Date(value)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}`
}

async function uploadPoster(eventId, file) {
  const formData = new FormData()
  formData.append('file', file)

  return requestJson(`/api/admin/events/${eventId}/upload-poster`, {
    method: 'POST',
    body: formData,
  })
}

function AdminCreateEventPage() {
  const navigate = useNavigate()
  const [formValues, setFormValues] = useState({
    title: '',
    description: '',
    event_date: '',
    venue_name: '',
    venue_address: '',
    producer_name: '',
    status: 'draft',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [posterPreview, setPosterPreview] = useState('')
  const [pendingPosterFile, setPendingPosterFile] = useState(null)

  function handlePosterSelect(changeEvent) {
    const file = changeEvent.target.files?.[0]
    if (!file) {
      return
    }

    setPosterPreview(URL.createObjectURL(file))
    setPendingPosterFile(file)
  }

  async function handleSubmit(submitEvent) {
    submitEvent.preventDefault()
    setSubmitting(true)
    setError('')

    try {
      const createdEvent = await requestJson('/api/admin/events', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...formValues,
          event_date: new Date(formValues.event_date).toISOString(),
        }),
      })

      if (pendingPosterFile) {
        await uploadPoster(createdEvent.id, pendingPosterFile)
      }

      navigate(`/admin/events/${createdEvent.id}`, {
        state: {
          successMessage: 'Event created successfully.',
        },
      })
    } catch (submitError) {
      setError(submitError.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="page-shell admin-page">
      <div className="admin-header">
        <div>
          <p className="eyebrow">Admin</p>
          <h1>Create Event</h1>
        </div>
        <Link className="admin-link" to="/admin">
          &larr; Back to events
        </Link>
      </div>

      <AdminEventForm
        mode="create"
        event={null}
        formValues={formValues}
        setFormValues={setFormValues}
        onSubmit={handleSubmit}
        submitting={submitting}
        error={error}
        successMessage=""
        posterPreview={posterPreview}
        onPosterSelect={handlePosterSelect}
      />
    </main>
  )
}

/* ──────────── Admin: Ticket Types Section ──────────── */

function TicketTypesSection({ eventId, ticketTypes, onReload }) {
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingTicketTypeId, setEditingTicketTypeId] = useState('')
  const [formValues, setFormValues] = useState({
    name: '',
    price: '',
    total_slots: '',
  })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  function resetForm() {
    setFormValues({
      name: '',
      price: '',
      total_slots: '',
    })
    setError('')
    setSubmitting(false)
  }

  function startAdd() {
    resetForm()
    setEditingTicketTypeId('')
    setShowAddForm(true)
  }

  function startEdit(ticketType) {
    setFormValues({
      name: ticketType.name,
      price: String(ticketType.price),
      total_slots: String(ticketType.total_slots),
    })
    setEditingTicketTypeId(ticketType.id)
    setShowAddForm(false)
    setError('')
  }

  async function handleSave(submitEvent) {
    submitEvent.preventDefault()
    setSubmitting(true)
    setError('')

    const payload = {
      name: formValues.name.trim(),
      price: Number(formValues.price),
      total_slots: Number(formValues.total_slots),
    }

    try {
      if (editingTicketTypeId) {
        await requestJson(`/api/admin/ticket-types/${editingTicketTypeId}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        })
      } else {
        await requestJson(`/api/admin/events/${eventId}/ticket-types`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        })
      }

      resetForm()
      setShowAddForm(false)
      setEditingTicketTypeId('')
      await onReload()
    } catch (saveError) {
      setError(saveError.message)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(ticketTypeId) {
    if (!window.confirm('Delete this ticket type?')) {
      return
    }

    try {
      await requestJson(`/api/admin/ticket-types/${ticketTypeId}`, {
        method: 'DELETE',
      })
      await onReload()
    } catch (deleteError) {
      setError(deleteError.message)
    }
  }

  return (
    <section className="admin-section">
      <div className="admin-section-header">
        <h2>Ticket Types</h2>
        <button className="admin-button secondary" type="button" onClick={startAdd}>
          + Add Ticket Type
        </button>
      </div>

      {error && <p className="status-message form-message">{error}</p>}

      <div className="admin-table-wrap" style={{ marginTop: 12 }}>
        <table className="admin-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Price</th>
              <th>Total Slots</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {ticketTypes.map((ticketType) => (
              <tr key={ticketType.id}>
                <td>{ticketType.name}</td>
                <td>{formatPrice(ticketType.price)}</td>
                <td>{ticketType.total_slots}</td>
                <td className="admin-actions-cell">
                  <button className="admin-link button-link" type="button" onClick={() => startEdit(ticketType)}>
                    Edit
                  </button>
                  <button
                    className="admin-link button-link"
                    type="button"
                    onClick={() => handleDelete(ticketType.id)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {ticketTypes.length === 0 && (
              <tr>
                <td colSpan="4">No ticket types yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {(showAddForm || editingTicketTypeId) && (
        <form className="inline-ticket-form" onSubmit={handleSave}>
          <input
            type="text"
            placeholder="Name"
            value={formValues.name}
            onChange={(event) => setFormValues((current) => ({ ...current, name: event.target.value }))}
            required
          />
          <input
            type="number"
            min="1"
            step="0.01"
            placeholder="Price"
            value={formValues.price}
            onChange={(event) => setFormValues((current) => ({ ...current, price: event.target.value }))}
            required
          />
          <input
            type="number"
            min="0"
            placeholder="Total slots"
            value={formValues.total_slots}
            onChange={(event) =>
              setFormValues((current) => ({ ...current, total_slots: event.target.value }))
            }
            required
          />
          <button className="admin-button" type="submit" disabled={submitting}>
            {submitting ? 'Saving...' : 'Save'}
          </button>
          <button
            className="admin-button secondary"
            type="button"
            onClick={() => {
              resetForm()
              setShowAddForm(false)
              setEditingTicketTypeId('')
            }}
          >
            Cancel
          </button>
        </form>
      )}
    </section>
  )
}

/* ──────────── Admin: Edit Event ──────────── */

function AdminEditEventPage() {
  const { id } = useParams()
  const location = useLocation()
  const [event, setEvent] = useState(null)
  const [formValues, setFormValues] = useState({
    title: '',
    description: '',
    event_date: '',
    venue_name: '',
    venue_address: '',
    producer_name: '',
    status: 'draft',
  })
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState(location.state?.successMessage || '')
  const [posterPreview, setPosterPreview] = useState('')

  async function loadEvent() {
    if (!id) {
      return
    }

    setLoading(true)
    try {
      const data = await fetchAdminEvent(id)
      setEvent(data)
      setFormValues({
        title: data.title || '',
        description: data.description || '',
        event_date: toDateTimeLocalString(data.event_date),
        venue_name: data.venue_name || '',
        venue_address: data.venue_address || '',
        producer_name: data.producer_name || '',
        status: data.status || 'draft',
      })
      setError('')
    } catch (loadError) {
      setError(loadError.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadEvent()
  }, [id])

  async function handlePosterSelect(changeEvent) {
    const file = changeEvent.target.files?.[0]
    if (!file || !id) {
      return
    }

    setPosterPreview(URL.createObjectURL(file))

    try {
      const payload = await uploadPoster(id, file)
      setEvent((currentEvent) => ({
        ...currentEvent,
        poster_url: payload.poster_url,
      }))
      setSuccessMessage('Poster uploaded successfully.')
      setError('')
    } catch (uploadError) {
      setError(uploadError.message)
      setSuccessMessage('')
    }
  }

  async function handleSubmit(submitEvent) {
    submitEvent.preventDefault()
    if (!id) {
      return
    }

    setSubmitting(true)
    setError('')

    try {
      const payload = await requestJson(`/api/admin/events/${id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...formValues,
          event_date: new Date(formValues.event_date).toISOString(),
        }),
      })

      setEvent(payload)
      setSuccessMessage('Event updated successfully.')
    } catch (submitError) {
      setError(submitError.message)
      setSuccessMessage('')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <main className="page-shell admin-page">
        <p className="status-message">Loading event...</p>
      </main>
    )
  }

  if (!event) {
    return (
      <main className="page-shell admin-page">
        <p className="status-message">{error || 'Event not found.'}</p>
      </main>
    )
  }

  return (
    <main className="page-shell admin-page">
      <div className="admin-header">
        <div>
          <p className="eyebrow">Admin</p>
          <h1>Edit Event</h1>
        </div>
        <Link className="admin-link" to="/admin">
          &larr; Back to events
        </Link>
      </div>

      <AdminEventForm
        mode="edit"
        event={event}
        formValues={formValues}
        setFormValues={setFormValues}
        onSubmit={handleSubmit}
        submitting={submitting}
        error={error}
        successMessage={successMessage}
        posterPreview={posterPreview}
        onPosterSelect={handlePosterSelect}
      />

      <TicketTypesSection eventId={id} ticketTypes={event.ticket_types || []} onReload={loadEvent} />
    </main>
  )
}

/* ──────────── App Router ──────────── */

function PublicLayout({ children }) {
  return (
    <>
      <Navbar />
      {children}
    </>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<PublicLayout><HomePage /></PublicLayout>} />
      <Route path="/events" element={<PublicLayout><EventListPage /></PublicLayout>} />
      <Route path="/classes" element={<PublicLayout><ClassesPage /></PublicLayout>} />
      <Route path="/events/:slug" element={<PublicLayout><EventDetailPage /></PublicLayout>} />
      <Route path="/events/:slug/checkout" element={<PublicLayout><CheckoutPage /></PublicLayout>} />
      <Route path="/orders/:booking_reference/confirmation" element={<PublicLayout><OrderConfirmationPage /></PublicLayout>} />
      <Route path="/admin" element={<AdminEventListPage />} />
      <Route path="/admin/events/new" element={<AdminCreateEventPage />} />
      <Route path="/admin/events/:id" element={<AdminEditEventPage />} />
    </Routes>
  )
}
