function closeHorseModal(){var y=state.modalScroll||0;state.horseModalNo=null;document.body.style.overflow='';render();window.scrollTo(0,y);if(state.race)scheduleHistoryPoll(state.race.id)}
