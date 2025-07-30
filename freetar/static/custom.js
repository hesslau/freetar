/*****************
 * BEGIN SCROLL STUFF
 *****************/

const SCROLL_STEP_SIZE = 3;
const SCROLL_TIMEOUT_MINIMUM = 50;
const SCROLL_DELAY_AFTER_USER_ACTION = 500;

let pausedForUserInteraction = false;
let scrollTimeout = 500;
let scrollInterval = null;
let pauseScrollTimeout = null;

$('#checkbox_autoscroll').prop("checked", false);


/*****************
* Event Handlers
*****************/

$('#checkbox_autoscroll').click(function () {
    if ($(this).is(':checked')) {
        startScrolling();
    } else {
        stopScrolling();
    }
});

$(window).on("wheel touchmove", function() {
    pauseScrolling(SCROLL_DELAY_AFTER_USER_ACTION);
});

$('#scroll_speed_down').click(function () {
    // Increase the delay to slow down scroll
    scrollTimeout += 50;
    if (scrollInterval !== null)
    {
        pauseScrolling(SCROLL_DELAY_AFTER_USER_ACTION);
        startScrolling();
    }
});

$('#scroll_speed_up').click(function () {
    // Decrease the delay to speed up scroll.
    // Don't decrease the delay all the way to 0
    scrollTimeout = Math.max(50, scrollTimeout - 50);

    if (scrollInterval !== null)
    {
        pauseScrolling(SCROLL_DELAY_AFTER_USER_ACTION);
        startScrolling();
    }
});


/*******************
 * Scroll Functions
 ******************/

// Scroll the page by SCROLL_STEP_SIZE
// Will not do anything if `pausedForUserInteraction` is set to `true`
function pageScroll() {
    if (pausedForUserInteraction) { return; }

    window.scrollBy(0, SCROLL_STEP_SIZE);
}

// Sets up the `pageScroll` function to be called in a loop every
// `scrollTimeout` milliseconds
function startScrolling() {
    if (scrollInterval) {
        clearInterval(scrollInterval);
    }
    scrollInterval = setInterval(pageScroll, scrollTimeout);
}

// Sets `pausedForUserInteraction` to `true` for `delay` milliseconds. 
// Will stop `pageScroll` from actually scrolling the page
function pauseScrolling(delay) {
    pausedForUserInteraction = true;
    clearTimeout(pauseScrollTimeout);
    pauseScrollTimeout = setTimeout(() => pausedForUserInteraction = false, delay);
}

// Clears the interval that got set up in `startScrolling`
function stopScrolling() {
    clearInterval(scrollInterval);
}


/*****************
 * DONE SCROLL STUFF
 *****************/

function colorize_favs() {
    // make every entry yellow if we faved it before
    fetch('/favorites')
        .then(response => response.json())
        .then(favorites => {
            $("#results tr").each(function () {
                var tab_url = $(this).find(".song").find("a").attr("href");
                if (tab_url && favorites[tab_url] != undefined) {
                    $(this).find(".favorite").css("color", "#ffae00");
                }
            });
        })
        .catch(error => {
            console.error('Error loading favorites:', error);
        });
}

function initialise_transpose() {
    let transpose_value = 0;
    const transposedSteps = $('#transposed_steps')
    const minus = $('#transpose_down')
    const plus = $('#transpose_up')
    plus.click(function () {
        transpose_value = Math.min(11, transpose_value + 1)
        transpose()
    });
    minus.click(function () {
        transpose_value = Math.max(-11, transpose_value - 1)
        transpose()
    });
    transposedSteps.click(function () {
        transpose_value = 0
        transpose()
    });

    $('.tab').find('.chord-root, .chord-bass').each(function () {
        const text = $(this).text()
        $(this).attr('data-original', text)
    })

    function transpose() {
        $('.tab').find('.chord-root, .chord-bass').each(function () {
            const originalText = $(this).attr('data-original')
            const transposedSteps = $('#transposed_steps')
            if (transpose_value === 0) {
                $(this).text(originalText)
                transposedSteps.hide()
            } else {
                const new_text = transpose_note(originalText.trim(), transpose_value)
                $(this).text(new_text)
                transposedSteps.text((transpose_value > 0 ? "+" : "") + transpose_value)
                transposedSteps.show()
            }
        });
    }

    // Defines a list of notes, grouped with any alternate names (like D# and Eb)
    const noteNames = [
        ['A'],
        ['A#', 'Bb'],
        ['B','Cb'],
        ['C', 'B#'],
        ['C#', 'Db'],
        ['D'],
        ['D#', 'Eb'],
        ['E', 'Fb'],
        ['F', 'E#'],
        ['F#', 'Gb'],
        ['G'],
        ['G#', 'Ab'],
    ];

    // Find the given note in noteNames, then step through the list to find the
    // next note up or down. Currently just selects the first note name that
    // matches. It doesn't preserve sharp, flat, or any try to determine what
    // key we're in.
    function transpose_note(note, transpose_value) {

        let noteIndex = noteNames.findIndex(tone => tone.includes(note));
        if (noteIndex === -1)
        {
            console.debug("Note ["+note+"] not found. Can't transpose");
            return note;
        }

        let new_index = (noteIndex + transpose_value) % 12;
        if (new_index < 0) {
            new_index += 12;
        }

        // TODO: Decide on sharp, flat, or natural
        return noteNames[new_index][0];
    }
}

$(document).ready(function () {
    colorize_favs();
    initialise_transpose();
});


$('#checkbox_view_chords').click(function(){
    if($(this).is(':checked')){
        $("#chordVisuals").show();
    } else {
        $("#chordVisuals").hide();
    }
});

$('#dark_mode').click(function(){
    if (document.documentElement.getAttribute('data-bs-theme') == 'dark') {
        document.documentElement.setAttribute('data-bs-theme', 'light');
        localStorage.setItem("dark_mode", false);
    }
    else {
        document.documentElement.setAttribute('data-bs-theme', 'dark');
        localStorage.setItem("dark_mode", true);
    }
});

// Update favorite click handler to use server-side storage
document.querySelectorAll('.favorite').forEach(item => {
  item.addEventListener('click', event => {
    const elm = event.target;
    const tab_url = elm.getAttribute('data-url');
    
    // Check if already favorited by checking current color
    const isFavorited = $(elm).css("color") === "rgb(255, 174, 0)"; // #ffae00 in rgb
    
    if (isFavorited) {
        // Remove from favorites
        fetch('/favorites', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ tab_url: tab_url })
        }).then(response => {
            if (response.ok) {
                $(elm).css("color", "");
            }
        }).catch(error => {
            console.error('Error removing favorite:', error);
        });
    } else {
        // Add to favorites
        const fav = {
            artist_name: elm.getAttribute('data-artist'),
            song: elm.getAttribute('data-song'),
            type: elm.getAttribute('data-type'),
            rating: elm.getAttribute('data-rating'),
            tab_url: tab_url
        };
        
        fetch('/favorites', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(fav)
        }).then(response => {
            if (response.ok) {
                $(elm).css("color", "#ffae00");
            }
        }).catch(error => {
            console.error('Error adding favorite:', error);
        });
    }
  })
})

// WebSocket connection
let socket = null;

function connectWebSocket() {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        const wsPort = window.location.port ? parseInt(window.location.port) + 1 : 22002;
        socket = new WebSocket(`ws://${window.location.hostname}:${wsPort}`);
        
        socket.onopen = () => {
            console.log('WebSocket connected');
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'share_page') {
                window.location.href = data.url;
            }
        };

        socket.onclose = () => {
            console.log('WebSocket disconnected');
            // Try to reconnect after 5 seconds
            setTimeout(connectWebSocket, 5000);
        };
    }
}

function shareCurrentPage() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        // Try to get artist and song from the favorite star element on the page
        let artist_name = "Unknown Artist";
        let song_name = "Unknown Song";
        
        const favoriteElement = document.querySelector('.favorite[data-artist][data-song]');
        if (favoriteElement) {
            artist_name = favoriteElement.getAttribute('data-artist') || "Unknown Artist";
            song_name = favoriteElement.getAttribute('data-song') || "Unknown Song";
        }
        
        // Store the current URL on the server as the last shared song with metadata
        fetch('/live', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                url: window.location.pathname,
                artist_name: artist_name,
                song_name: song_name
            })
        }).then(() => {
            // Refresh the live banner after sharing
            loadLiveBanner();
        });
        
        socket.send(JSON.stringify({
            type: 'share_page',
            url: window.location.pathname
        }));
        // Show a brief notification
        const shareIcon = document.getElementById('share-icon');
        const originalText = shareIcon.textContent;
        shareIcon.textContent = '✓';
        setTimeout(() => {
            shareIcon.textContent = originalText;
        }, 2000);
    } else {
        console.error('WebSocket not connected');
        // Show error state
        const shareIcon = document.getElementById('share-icon');
        const originalText = shareIcon.textContent;
        shareIcon.textContent = '⚠️';
        setTimeout(() => {
            shareIcon.textContent = originalText;
        }, 2000);
    }
}

function showRecentShares() {
    // Get recent shares from the server
    fetch('/live')
        .then(response => {
            if (response.ok) {
                return response.json();
            } else {
                throw new Error('No recent shares');
            }
        })
        .then(data => {
            if (data.shares && data.shares.length > 0) {
                showRecentSharesModal(data.shares);
            } else {
                throw new Error('No recent shares');
            }
        })
        .catch(error => {
            // Show notification if no songs have been shared yet
            const recentBtn = document.getElementById('recent-shares-btn');
            const recentIcon = recentBtn.querySelector('div');
            const originalText = recentIcon.textContent;
            recentIcon.textContent = '❌';
            setTimeout(() => {
                recentIcon.textContent = originalText;
            }, 2000);
        });
}

function showRecentSharesModal(shares) {
    // Create a simple modal-like overlay
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.5); z-index: 1000;
        display: flex; align-items: center; justify-content: center;
    `;
    
    const modal = document.createElement('div');
    modal.style.cssText = `
        background: var(--bs-body-bg, white); border-radius: 8px;
        padding: 20px; max-width: 700px; width: 95%;
        max-height: 80vh; overflow-y: auto;
        color: var(--bs-body-color, black);
        border: 1px solid var(--bs-border-color, #dee2e6);
    `;
    
    let modalContent = '<h5>📋 Recent Shares</h5>';
    modalContent += '<div style="margin-top: 15px; overflow-x: auto;">';
    modalContent += `
        <table style="width: 100%; border-collapse: collapse; font-size: 0.9em;">
            <thead>
                <tr style="border-bottom: 2px solid var(--bs-border-color, #dee2e6);">
                    <th style="padding: 8px; text-align: left; font-weight: bold;">Artist</th>
                    <th style="padding: 8px; text-align: left; font-weight: bold;">Song</th>
                    <th style="padding: 8px; text-align: left; font-weight: bold;">Shared</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    shares.forEach((share, index) => {
        // Use stored artist and song names, with fallback to URL parsing if not available
        let artist = share.artist_name || 'Unknown Artist';
        let song = share.song_name || 'Unknown Song';
        
        // Fallback to URL parsing for older entries that might not have stored names
        if (!share.artist_name && !share.song_name) {
            const pathParts = share.url.split('/');
            if (pathParts.length >= 4 && pathParts[1] === 'tab') {
                artist = decodeURIComponent(pathParts[2]).replace(/[-_]/g, ' ');
                song = decodeURIComponent(pathParts[3]).replace(/[-_]/g, ' ');
            }
        }
        
        // Format timestamp
        let timeString = 'Unknown time';
        try {
            const date = new Date(share.timestamp);
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMs / 3600000);
            const diffDays = Math.floor(diffMs / 86400000);
            
            if (diffMins < 1) {
                timeString = 'Just now';
            } else if (diffMins < 60) {
                timeString = `${diffMins}m ago`;
            } else if (diffHours < 24) {
                timeString = `${diffHours}h ago`;
            } else if (diffDays < 7) {
                timeString = `${diffDays}d ago`;
            } else {
                timeString = date.toLocaleDateString();
            }
        } catch (e) {
            console.error('Error parsing timestamp:', share.timestamp);
        }
        
        const isLatest = index === 0;
        modalContent += `
            <tr style="border-bottom: 1px solid var(--bs-border-color, #eee); cursor: pointer; transition: background-color 0.2s;"
                onmouseover="this.style.backgroundColor='var(--bs-light, #f8f9fa)'"
                onmouseout="this.style.backgroundColor='transparent'"
                onclick="window.location.href='${share.url}'; closeRecentSharesModal();">
                <td style="padding: 10px; font-weight: ${isLatest ? 'bold' : 'normal'};">${artist}</td>
                <td style="padding: 10px; font-weight: ${isLatest ? 'bold' : 'normal'};">${song}${isLatest ? ' <span style="color: #28a745; font-size: 0.8em;">• Latest</span>' : ''}</td>
                <td style="padding: 10px; color: var(--bs-secondary, #6c757d); font-size: 0.85em;">${timeString}</td>
            </tr>
        `;
    });
    
    modalContent += `
            </tbody>
        </table>
    </div>
    <div style="margin-top: 20px; text-align: right;">
        <button onclick="closeRecentSharesModal()" 
                style="padding: 8px 16px; border: none; background: #6c757d; color: white; 
                       border-radius: 4px; cursor: pointer; transition: background-color 0.2s;"
                onmouseover="this.style.backgroundColor='#5a6268'"
                onmouseout="this.style.backgroundColor='#6c757d'">Close</button>
    </div>
    `;
    
    modal.innerHTML = modalContent;
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    
    // Store reference for closing
    window.currentRecentSharesModal = overlay;
    
    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            closeRecentSharesModal();
        }
    });
}

function closeRecentSharesModal() {
    if (window.currentRecentSharesModal) {
        document.body.removeChild(window.currentRecentSharesModal);
        window.currentRecentSharesModal = null;
    }
}

function loadLiveBanner() {
    fetch('/live')
        .then(response => {
            if (response.ok) {
                return response.json();
            } else {
                throw new Error('No recent shares');
            }
        })
        .then(data => {
            if (data.shares && data.shares.length > 0) {
                // Show the most recent share in the banner
                showLiveBanner(data.shares[0].url, data.shares[0]);
            } else {
                hideLiveBanner();
            }
        })
        .catch(error => {
            hideLiveBanner();
        });
}

function showLiveBanner(url, share_data = null) {
    const banner = document.getElementById('live-banner');
    const link = document.getElementById('live-banner-link');
    
    let songText = 'Unknown Song';
    
    // Use stored data if available, otherwise parse URL
    if (share_data && share_data.artist_name && share_data.song_name) {
        songText = `${share_data.artist_name} - ${share_data.song_name}`;
    } else {
        // Fallback to URL parsing
        const pathParts = url.split('/');
        if (pathParts.length >= 4 && pathParts[1] === 'tab') {
            const artist = decodeURIComponent(pathParts[2]).replace(/[-_]/g, ' ');
            const song = decodeURIComponent(pathParts[3]).replace(/[-_]/g, ' ');
            songText = `${artist} - ${song}`;
        }
    }
    
    link.href = url;
    link.textContent = songText;
    banner.classList.remove('d-none');
}

function hideLiveBanner() {
    const banner = document.getElementById('live-banner');
    banner.classList.add('d-none');
}

// Connect WebSocket when page loads
document.addEventListener('DOMContentLoaded', function() {
    connectWebSocket();
    loadLiveBanner();
});

