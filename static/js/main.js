document.addEventListener("DOMContentLoaded", function() {

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
            init: function() {
                var activeSlide = document.querySelector('.swiper-slide-active');
                if (activeSlide) {
                    var activeAudio = activeSlide.querySelector('.voiceover');
                    if (activeAudio) {
                        activeAudio.loop = true;
                        activeAudio.play().catch(function(error) {
                           console.log("Audio autoplay error on init:", error);
                        });
                    }
                    var activeVideo = activeSlide.querySelector('.reel-video');
                    if (activeVideo) {
                        activeVideo.play().catch(function(error) {
                           console.log("Video autoplay error on init:", error);
                        });
                    }
                }
            },
            slideChangeTransitionStart: function() {
                document.querySelectorAll('.voiceover').forEach(function(audio) {
                    audio.pause();
                    audio.currentTime = 0;
                });
                document.querySelectorAll('.reel-video').forEach(function(video) {
                    video.pause();
                    video.currentTime = 0;
                });
            },
            slideChangeTransitionEnd: function() {
                var activeSlide = document.querySelector('.swiper-slide-active');
                if (activeSlide) {
                    var activeAudio = activeSlide.querySelector('.voiceover');
                    if (activeAudio) {
                        activeAudio.loop = true;
                        activeAudio.play().catch(function(error) {
                           console.log("Audio autoplay error on slide change:", error);
                        });
                    }
                    var activeVideo = activeSlide.querySelector('.reel-video');
                    if (activeVideo) {
                        activeVideo.play().catch(function(error) {
                           console.log("Video autoplay error on slide change:", error);
                        });
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
  });
  