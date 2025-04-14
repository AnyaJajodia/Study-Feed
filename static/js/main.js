document.addEventListener("DOMContentLoaded", function() {

    function startSubtitleSync(audioElement, subtitleOverlay, subtitles) {
        // Clear any existing interval.
        if (audioElement.subtitleInterval) {
            clearInterval(audioElement.subtitleInterval);
        }
        
        const blockSize = 5;
        audioElement.subtitleInterval = setInterval(function() {
            var currentTime = audioElement.currentTime;
            
            // Find the index of the first word whose end time is still in the future.
            var activeWordIndex = subtitles.findIndex(function(item) {
                return currentTime < Number(item.end);
            });
            
            if (activeWordIndex === -1) {
                // All words have been processed.
                subtitleOverlay.innerText = "";
                return;
            }
            
            // Determine which block of 5 the active word belongs to.
            var blockIndex = Math.floor(activeWordIndex / blockSize);
            var startIndex = blockIndex * blockSize;
            var endIndex = Math.min(startIndex + blockSize, subtitles.length);
            
            // Display the entire block.
            var blockWords = subtitles.slice(startIndex, endIndex);
            subtitleOverlay.innerText = blockWords.map(function(item) {
                return item.word;
            }).join(" ");
        }, 100); // Check every 100ms.
    }
    
    
    
    var swiper = new Swiper('.swiper-container', {
        direction: 'vertical',
        loop: false,
        mousewheel: {
           sensitivity: 0.1, 
           forceToAxis: true,
           thresholdDelta: 5,
           thresholdTime: 200
        },
        pagination: {
           el: '.swiper-pagination',
           clickable: true,
        },
        on: {
            // On Swiper initialization:
            init: function() {
                var activeSlide = document.querySelector('.swiper-slide-active');
                if (activeSlide) {
                    var activeAudio = activeSlide.querySelector('.voiceover');
                    var activeVideo = activeSlide.querySelector('.reel-video');
                    if (activeAudio) {
                        activeAudio.loop = true;
                        activeAudio.play().catch(function(error) {
                           console.log("Audio autoplay error on init:", error);
                        });
                    }
                    if (activeVideo) {
                        activeVideo.play().catch(function(error) {
                           console.log("Video autoplay error on init:", error);
                        });
                    }
                    // Debug: log subtitles data attribute
                    var subtitleOverlay = activeSlide.querySelector('.subtitle-overlay');
                    if (subtitleOverlay) {
                        var subtitlesData = subtitleOverlay.getAttribute('data-subtitles');
                        console.log("Raw subtitles data on init:", subtitlesData);
                        if (subtitlesData) {
                            try {
                                var subtitles = JSON.parse(subtitlesData);
                                console.log("Parsed subtitles on init:", subtitles);
                                startSubtitleSync(activeAudio, subtitleOverlay, subtitles);
                            } catch(e) {
                                console.error("Error parsing subtitles JSON on init:", e);
                            }
                        }
                    }
                }
            },
            // When slide transition starts, pause and reset audio/video and clear subtitle sync.
            slideChangeTransitionStart: function() {
                document.querySelectorAll('.voiceover').forEach(function(audio) {
                    audio.pause();
                    audio.currentTime = 0;
                    if (audio.subtitleInterval) clearInterval(audio.subtitleInterval);
                });
                document.querySelectorAll('.reel-video').forEach(function(video) {
                    video.pause();
                    video.currentTime = 0;
                });
            },
            // Once slide transition ends, restart audio/video and subtitle syncing.
            slideChangeTransitionEnd: function() {
                var activeSlide = document.querySelector('.swiper-slide-active');
                if (activeSlide) {
                    var activeAudio = activeSlide.querySelector('.voiceover');
                    var activeVideo = activeSlide.querySelector('.reel-video');
                    if (activeAudio) {
                        activeAudio.loop = true;
                        activeAudio.play().catch(function(error) {
                           console.log("Audio autoplay error on slide change:", error);
                        });
                    }
                    if (activeVideo) {
                        activeVideo.play().catch(function(error) {
                           console.log("Video autoplay error on slide change:", error);
                        });
                    }
                    // Debug: log subtitles data attribute on slide change.
                    var subtitleOverlay = activeSlide.querySelector('.subtitle-overlay');
                    if (activeAudio && subtitleOverlay) {
                        var subtitlesData = subtitleOverlay.getAttribute('data-subtitles');
                        console.log("Raw subtitles data on slide change:", subtitlesData);
                        if (subtitlesData) {
                            try {
                                var subtitles = JSON.parse(subtitlesData);
                                console.log("Parsed subtitles on slide change:", subtitles);
                                startSubtitleSync(activeAudio, subtitleOverlay, subtitles);
                            } catch(e) {
                                console.error("Error parsing subtitles JSON on slide change:", e);
                            }
                        }
                    }
                }
            }
        }
    });


      
    var nextBtn = document.getElementById("nextBtn");
    if (nextBtn) {
      nextBtn.addEventListener("click", function() {
        swiper.slideNext();
      });
    }
      
    var prevBtn = document.getElementById("prevBtn");
    if (prevBtn) {
      prevBtn.addEventListener("click", function() {
        swiper.slidePrev();
      });
    }
  
    // Toggle comment panel when the Comment button is clicked
    document.querySelectorAll('.comment-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var slideWrapper = this.closest('.slide-wrapper');
        slideWrapper.classList.toggle('show-comments');
      });
    });
  
    // Handle comment submission via AJAX (Fetch)
    document.querySelectorAll('.submit-comment').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var commentPanel = this.closest('.comment-panel');
        var reelIdElem = commentPanel.querySelector('.reel-id');
        var commentInput = commentPanel.querySelector('.comment-input');
        var commentsList = commentPanel.querySelector('.comments-list');
        
        var reelId = reelIdElem.value;
        var commentText = commentInput.value.trim();
        
        if (!commentText) {
          alert("Please enter a comment.");
          return;
        }
        
        var formData = new FormData();
        formData.append('reel_id', reelId);
        formData.append('comment', commentText);
        
        fetch('/add_comment', {
          method: 'POST',
          body: formData
        })
        .then(response => {
          const contentType = response.headers.get("content-type");
          if (contentType && contentType.indexOf("application/json") !== -1) {
            return response.json();
          } else {
            throw new Error("Response is not JSON");
          }
        })
        .then(data => {
          if (data.status === 'success') {
            // Create a new comment element using createElement
            var newCommentDiv = document.createElement('div');
            newCommentDiv.className = 'comment-item';
            newCommentDiv.setAttribute('data-comment-id', data.comment.id);
            // Set the innerHTML for the new comment (only text and delete button)
            newCommentDiv.innerHTML = '<small>' + data.comment.content + '</small> ' +
                                      '<button class="btn btn-link btn-sm delete-comment">Delete</button>';
            if (commentsList) {
              commentsList.appendChild(newCommentDiv);
            }
            // Clear the input
            commentInput.value = '';
          } else {
            alert("Error: " + data.message);
          }
        })
        .catch(error => {
          console.error("Error submitting comment:", error);
          alert("An error occurred while submitting your comment.");
        });
      });
    });
  
    // Use event delegation to handle clicks on delete-comment buttons
    document.addEventListener("click", function(event) {
      if (event.target && event.target.classList.contains("delete-comment")) {
        var commentItem = event.target.closest(".comment-item");
        if (!commentItem) {
          console.error("Could not find comment item element.");
          return;
        }
        var commentId = commentItem.getAttribute("data-comment-id");
        if (!commentId) {
          alert("Comment ID not found.");
          return;
        }
        
        fetch('/delete_comment/' + commentId, {
          method: 'POST'
        })
        .then(response => {
          const contentType = response.headers.get("content-type");
          if (contentType && contentType.indexOf("application/json") !== -1) {
            return response.json();
          } else {
            throw new Error("Response is not JSON");
          }
        })
        .then(data => {
          if (data.status === 'success') {
            commentItem.remove();
          } else {
            alert("Error: " + data.message);
          }
        })
        .catch(error => {
          console.error("Error deleting comment:", error);
          alert("An error occurred while deleting the comment.");
        });
      }
    });

      // --- Live search for For You feeds ---
  var feedSearchInput = document.getElementById("feed-search-input");
  var feedListContainer = document.getElementById("feed-list-container");
  if (feedSearchInput && feedListContainer) {
      feedSearchInput.addEventListener("input", function() {
          var query = feedSearchInput.value;
          fetch('/search_feed?q=' + encodeURIComponent(query))
            .then(response => response.json())
            .then(data => {
              // Clear existing feed cards
              feedListContainer.innerHTML = "";
              if (data.length === 0) {
                  feedListContainer.innerHTML = '<div class="alert alert-info">No For You pages found.</div>';
              } else {
                  // For each returned feed, create a card element and add it to the container
                  data.forEach(function(feed) {
                      var colDiv = document.createElement("div");
                      colDiv.className = "col-md-4";
                      colDiv.innerHTML = '<div class="card">' +
                          '<div class="card-body">' +
                          '<h5 class="card-title dark-font">' + feed.name + '</h5>' +
                          '<a href="' + feed.url + '" class="btn btn-sm btn-primary">Resume</a> ' +
                          '<a href="/delete_feed/' + feed.id + '" class="btn btn-sm btn-danger">Delete</a>' +
                          '</div>' +
                          '</div>';
                      feedListContainer.appendChild(colDiv);
                  });
              }
          })
          .catch(function(error) { console.error("Error with live search:", error); });
      });
  }

});
  